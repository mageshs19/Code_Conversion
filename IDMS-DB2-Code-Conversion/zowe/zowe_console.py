# LOCATION: zowe/zowe_console.py
# ACTION: REPLACE ENTIRE FILE
"""Console rendering for the pipeline. Printing and logging only."""

from __future__ import annotations

import logging
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

WIDTH = 80
INNER = WIDTH - 4
HEAVY = "=" * WIDTH
LIGHT = "-" * INNER
INDENT = "  "

BAR_WIDTH = 20
BAR_FULL = "#"
STAMP_FORMAT = "%d-%m-%Y %H:%M:%S"

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%d-%m-%Y %H:%M:%S"
LOGGER_NAME = "idms_db2_zowe"

_STATUS_WIDTH = 11


def banner(title: str) -> None:
    print("")
    print(HEAVY)
    print(f"{INDENT}{title.upper()}")
    print(f"{INDENT}Started {datetime.now().strftime(STAMP_FORMAT)}")
    print(HEAVY)


def footer() -> None:
    print("")
    print(f"{INDENT}Finished {datetime.now().strftime(STAMP_FORMAT)}")
    print(HEAVY)


def section(title: str) -> None:
    print("")
    print(f"{INDENT}{title.upper()}")
    print(f"{INDENT}{LIGHT}")


def row(label: str, value) -> None:
    print(f"{INDENT}{str(label):<22}{value}")


def bullets(lines) -> None:
    for line in lines:
        print(f"{INDENT}  {line}")


def warnings(lines) -> None:
    for line in lines:
        print(f"{INDENT}  ! {line}")


def step_line(index: int, total: int, label: str, status: str, seconds: float) -> None:
    bar = BAR_FULL * BAR_WIDTH
    print(
        f"{INDENT}[{index}/{total}] {label:<22}"
        f"[{bar}] {status:<{_STATUS_WIDTH}}{seconds:>6.1f}s"
    )


def verdict(text: str) -> None:
    print("")
    print(f"{INDENT}{text}")


def header(title: str) -> None:
    """Backward compatible with the earlier plain header."""
    section(title)


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


def credentials(artifact: str, connection) -> None:
    row("Host", f"{connection.host or '(not set)'}:{connection.port}")
    row("", f"from {setting_source(artifact, NAME_HOST)}")
    row("User", mask(NAME_USER, connection.user))
    row("", f"from {setting_source(artifact, NAME_USER)}")
    row("Password", mask(NAME_PASSWORD, connection.password))
    row("Verify TLS", connection.verify_tls)


def summary(results) -> None:
    section("summary")
    print(f"{INDENT}{'Step':<12}{'Status':<14}{'Seconds':>9}")
    print(f"{INDENT}{LIGHT}")
    total = 0.0
    failures = 0
    for result in results:
        print(
            f"{INDENT}{result.step:<12}{result.status:<14}{result.seconds:>9.1f}"
        )
        total += result.seconds
        if result.status == STATUS_FAILED:
            failures += 1
    print(f"{INDENT}{LIGHT}")
    print(f"{INDENT}Total {total:.1f}s     Failures {failures}")