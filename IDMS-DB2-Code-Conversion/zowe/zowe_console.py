# LOCATION: zowe/zowe_console.py
# ACTION: CREATE NEW FILE
"""Console output helpers for the pipeline.

Printing and logging only. No workspace knowledge, no HTTP, no steps.
"""

from __future__ import annotations

import logging
import sys

from zowe.zowe_env import mask, setting_source
from zowe.zowe_rules import (
    NAME_HOST,
    NAME_PASSWORD,
    NAME_USER,
    SUMMARY_HEADER,
    SUMMARY_ROW_TEMPLATE,
)

RULE_LINE = "-" * 74
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%d-%m-%Y %H:%M:%S"
LOGGER_NAME = "idms_db2_zowe"


def header(title: str) -> None:
    print("")
    print(title)
    print(RULE_LINE)


def bullets(lines) -> None:
    for line in lines:
        print(f"- {line}")


def warnings(lines) -> None:
    for line in lines:
        print(f"! {line}")


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        stream=sys.stdout,
    )


def logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def credentials(artifact: str, connection) -> None:
    """Connection block for the show command. Passwords are masked."""
    print(f"  Host         : {connection.host or '(not set)'}:{connection.port}")
    print(f"                 from {setting_source(artifact, NAME_HOST)}")
    print(f"  User         : {mask(NAME_USER, connection.user)}")
    print(f"                 from {setting_source(artifact, NAME_USER)}")
    print(f"  Password     : {mask(NAME_PASSWORD, connection.password)}")
    print(f"                 from {setting_source(artifact, NAME_PASSWORD)}")
    print(f"  Verify TLS   : {connection.verify_tls}")


def summary(results) -> None:
    header("Summary")
    print(SUMMARY_HEADER)
    print(RULE_LINE)
    for result in results:
        print(
            SUMMARY_ROW_TEMPLATE.format(
                step=result.step,
                status=result.status,
                seconds=result.seconds,
            )
        )