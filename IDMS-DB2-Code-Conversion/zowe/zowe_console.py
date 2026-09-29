# LOCATION: zowe/zowe_console.py
# ACTION: REPLACE ENTIRE FILE
"""Console rendering for the pipeline. Printing and logging only.

Presentation matches the batch console the COBOL team already reads:
counter, padded label, progress bar, padded status, seconds. Padding is
applied BEFORE colouring so escape codes never affect alignment.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime

from zowe.zowe_rules import (
    BAR_EMPTY_ASCII,
    BAR_EMPTY_UNICODE,
    BAR_FILLED_ASCII,
    BAR_FILLED_UNICODE,
    COLOUR_DIM,
    COLOUR_GREEN,
    COLOUR_RED,
    COLOUR_RESET,
    COLOUR_YELLOW,
    LOG_DATE_FORMAT,
    LOG_FORMAT,
    LOGGER_NAME,
    NO_COLOUR_ENV,
    STATUS_FAILED,
    STATUS_NOTHING,
    STATUS_OK,
    STATUS_SKIPPED,
)

WIDTH = 80
HEAVY = "=" * WIDTH
LIGHT = "-" * (WIDTH - 4)
INDENT = "  "
BAR_WIDTH = 20
LABEL_WIDTH = 22
STATUS_WIDTH = 9
STAMP_FORMAT = "%d-%m-%Y %H:%M:%S"

STATUS_COLOURS = {
    STATUS_OK: COLOUR_GREEN,
    STATUS_FAILED: COLOUR_RED,
    STATUS_SKIPPED: COLOUR_DIM,
    STATUS_NOTHING: COLOUR_YELLOW,
}


def _colour_enabled() -> bool:
    if os.environ.get(NO_COLOUR_ENV):
        return False
    try:
        return bool(sys.stdout.isatty())
    except Exception:  # noqa: BLE001
        return False


def _glyphs() -> tuple[str, str]:
    """Block glyphs when the code page can encode them, else ASCII."""
    encoding = getattr(sys.stdout, "encoding", "") or ""
    try:
        BAR_FILLED_UNICODE.encode(encoding)
        return BAR_FILLED_UNICODE, BAR_EMPTY_UNICODE
    except (LookupError, UnicodeEncodeError, AttributeError):
        return BAR_FILLED_ASCII, BAR_EMPTY_ASCII


FILLED, EMPTY = _glyphs()
COLOUR = _colour_enabled()


def _paint(text: str, code: str) -> str:
    if not COLOUR or not code:
        return text
    return f"{code}{text}{COLOUR_RESET}"


def _status_cell(status: str) -> str:
    return _paint(str(status).ljust(STATUS_WIDTH), STATUS_COLOURS.get(status, ""))


def banner(title: str) -> None:
    print("")
    print(HEAVY)
    print(f"{INDENT}{title.upper()}")
    print(f"{INDENT}Started {datetime.now().strftime(STAMP_FORMAT)}")
    print(HEAVY)


def section(title: str) -> None:
    print("")
    print(f"{INDENT}{title.upper()}")
    print(f"{INDENT}{LIGHT}")


def header(title: str) -> None:
    section(title)


def row(label: str, value) -> None:
    print(f"{INDENT}{str(label):<22}{value}")


def bullets(lines) -> None:
    for line in lines:
        print(f"{INDENT}  {line}")


def warnings(lines) -> None:
    for line in lines:
        print(f"{INDENT}! {line}")


def step_start(index: int, total: int, label: str) -> None:
    print("")
    print(f"{INDENT}[{index}/{total}] {label.upper()}")
    print(f"{INDENT}{LIGHT}")


def step_line(index: int, total: int, label: str, status: str, seconds: float) -> None:
    filled = BAR_WIDTH if status == STATUS_OK else BAR_WIDTH // 2
    bar = FILLED * filled + EMPTY * (BAR_WIDTH - filled)
    print(
        f"{INDENT}[{index}/{total}] {label:<{LABEL_WIDTH}}"
        f"[{bar}] {_status_cell(status)}{seconds:>7.1f}s"
    )


def summary(results) -> None:
    section("summary")
    print(f"{INDENT}{'Step':<12}{'Status':<14}{'Seconds':>9}")
    print(f"{INDENT}{LIGHT}")
    total = 0.0
    failures = 0
    for result in results:
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
    print(HEAVY)


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