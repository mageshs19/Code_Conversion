# LOCATION: zowe/zowe_console.py
# ACTION: REPLACE ENTIRE FILE
"""Console rendering for the pipeline. Printing and logging only.

SELF-CONTAINED BY DESIGN
========================
Presentation constants (bar glyphs, colours, widths, stamp format) live
HERE, not in zowe_rules. The previous version imported them from the
rules module, which owns mainframe facts - artifacts, libraries,
diagnostics - and knows nothing about a terminal. That coupling failed
at import time the moment a glyph name was missing.

Only STATUS_* and NAME_* are imported, because those are shared FACTS
that zowe_pipeline_steps.py and zowe_env.py also read.

PUBLIC API - unchanged, do not shrink it:
    banner, footer, section, header, row, bullets, warnings,
    step_start, step_line, summary, verdict,
    credentials, configure_logging, logger
`zowe_commands.py` imports bullets/credentials/header and
`zowe_pipeline.py` imports configure_logging/header/logger/summary.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime

from zowe.zowe_env import mask, setting_source
from zowe.zowe_rules import (
    NAME_HOST,
    NAME_PASSWORD,
    NAME_USER,
    STATUS_FAILED,
    STATUS_NOTHING,
    STATUS_OK,
    STATUS_SKIPPED,
)

# ----------------------------------------------------------- geometry
WIDTH = 80
INNER = WIDTH - 4
HEAVY = "=" * WIDTH
LIGHT = "-" * INNER
INDENT = "  "
BAR_WIDTH = 20
LABEL_WIDTH = 22
ROW_LABEL_WIDTH = 22
STATUS_WIDTH = 9
STAMP_FORMAT = "%d-%m-%Y %H:%M:%S"

LOGGER_NAME = "idms_db2_zowe"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%d-%m-%Y %H:%M:%S"

# ------------------------------------------------------------- glyphs
BAR_FILLED_UNICODE = "\u2588"
BAR_EMPTY_UNICODE = "\u2591"
BAR_FILLED_ASCII = "#"
BAR_EMPTY_ASCII = "_"

# ------------------------------------------------------------ colours
NO_COLOUR_ENV = "NO_COLOR"
COLOUR_RESET = "\033[0m"
COLOUR_DIM = "\033[2m"
COLOUR_GREEN = "\033[32m"
COLOUR_RED = "\033[31m"
COLOUR_YELLOW = "\033[33m"

STATUS_COLOURS = {
    STATUS_OK: COLOUR_GREEN,
    STATUS_FAILED: COLOUR_RED,
    STATUS_SKIPPED: COLOUR_DIM,
    STATUS_NOTHING: COLOUR_YELLOW,
}


# --------------------------------------------------------- capability
def _detect_colour() -> bool:
    if os.environ.get(NO_COLOUR_ENV):
        return False
    try:
        return bool(sys.stdout.isatty())
    except Exception:  # noqa: BLE001
        return False


def _detect_glyphs() -> tuple[str, str]:
    """Block glyphs when the code page can encode them, else ASCII.

    A legacy Windows code page raises UnicodeEncodeError on the block
    characters, which would abort the run over a cosmetic choice.
    """
    encoding = getattr(sys.stdout, "encoding", "") or ""
    try:
        BAR_FILLED_UNICODE.encode(encoding)
        return BAR_FILLED_UNICODE, BAR_EMPTY_UNICODE
    except (LookupError, UnicodeEncodeError, AttributeError):
        return BAR_FILLED_ASCII, BAR_EMPTY_ASCII


COLOUR = _detect_colour()
FILLED, EMPTY = _detect_glyphs()


def _paint(text: str, code: str) -> str:
    if not COLOUR or not code:
        return str(text)
    return f"{code}{text}{COLOUR_RESET}"


def _status_cell(status: str) -> str:
    """Pad BEFORE colouring, so escape codes never affect alignment."""
    return _paint(str(status).ljust(STATUS_WIDTH), STATUS_COLOURS.get(status, ""))


# ------------------------------------------------------------ blocks
def banner(title: str) -> None:
    print("")
    print(HEAVY)
    print(f"{INDENT}{str(title).upper()}")
    print(f"{INDENT}Started {datetime.now().strftime(STAMP_FORMAT)}")
    print(HEAVY)


def footer() -> None:
    print("")
    print(f"{INDENT}Finished {datetime.now().strftime(STAMP_FORMAT)}")
    print(HEAVY)


def section(title: str) -> None:
    print("")
    print(f"{INDENT}{str(title).upper()}")
    print(f"{INDENT}{LIGHT}")


def header(title: str) -> None:
    """Backward compatible with the earlier plain header."""
    section(title)


def row(label: str, value) -> None:
    print(f"{INDENT}{str(label):<{ROW_LABEL_WIDTH}}{value}")


def bullets(lines) -> None:
    for line in lines or []:
        print(f"{INDENT}  {line}")


def warnings(lines) -> None:
    for line in lines or []:
        print(f"{INDENT}! {line}")


# ------------------------------------------------------------- steps
def step_start(index: int, total: int, label: str) -> None:
    print("")
    print(f"{INDENT}[{index}/{total}] {str(label).upper()}")
    print(f"{INDENT}{LIGHT}")


def step_line(index: int, total: int, label: str, status: str, seconds: float) -> None:
    filled = BAR_WIDTH if status == STATUS_OK else BAR_WIDTH // 2
    bar = FILLED * filled + EMPTY * (BAR_WIDTH - filled)
    print(
        f"{INDENT}[{index}/{total}] {str(label):<{LABEL_WIDTH}}"
        f"[{bar}] {_status_cell(status)}{seconds:>7.1f}s"
    )


def summary(results) -> None:
    section("summary")
    print(f"{INDENT}{'Step':<12}{'Status':<14}{'Seconds':>9}")
    print(f"{INDENT}{LIGHT}")

    total = 0.0
    failures = 0
    for result in results or []:
        print(
            f"{INDENT}{result.step:<12}"
            f"{_status_cell(result.status):<14}"
            f"{result.seconds:>9.1f}"
        )
        total += result.seconds
        if result.status == STATUS_FAILED:
            failures += 1

    print(f"{INDENT}{LIGHT}")
    print(f"{INDENT}Total {total:.1f}s     Failures {failures}")


def verdict(text: str, failed: bool = False) -> None:
    print("")
    print(f"{INDENT}{_paint(text, COLOUR_RED if failed else COLOUR_GREEN)}")


# ------------------------------------------------------- credentials
def credentials(artifact: str, connection) -> None:
    """Report host / user / password source. The password is masked.

    getattr is used deliberately: a renamed field on ZoweConnection must
    degrade to a blank row, never abort the run.
    """
    host = getattr(connection, "host", "")
    port = getattr(connection, "port", "")
    user = getattr(connection, "user", "")
    password = getattr(connection, "password", "")

    row(NAME_HOST, f"{host}:{port}  [{setting_source(artifact, NAME_HOST)}]")
    row(NAME_USER, f"{user}  [{setting_source(artifact, NAME_USER)}]")
    row(
        NAME_PASSWORD,
        f"{mask(password)}  [{setting_source(artifact, NAME_PASSWORD)}]",
    )


# ----------------------------------------------------------- logging
def configure_logging(verbose: bool) -> None:
    """Quiet by default. Only WARNING and above reach the console."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        stream=sys.stdout,
    )
    if not verbose:
        logging.getLogger("urllib3").setLevel(logging.ERROR)


def logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


__all__ = [
    "banner",
    "footer",
    "section",
    "header",
    "row",
    "bullets",
    "warnings",
    "step_start",
    "step_line",
    "summary",
    "verdict",
    "credentials",
    "configure_logging",
    "logger",
]