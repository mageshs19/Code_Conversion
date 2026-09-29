# LOCATION: zowe/zowe_step_output.py
# ACTION: CREATE NEW FILE
"""Reads meaning out of a runner's console output.

The pipeline launches each runner as a SUBPROCESS, so its stdout IS the
contract. This module turns that text into a small dict of facts the
console can render in six lines instead of four hundred.

PATTERNS LIVE HERE, DELIBERATELY
================================
Project convention puts regex in zowe_patterns.py. This module is the
exception: every pattern below matches ONE runner's wording and has no
other consumer, so splitting it across two files would mean two places
to edit whenever that wording changes. No program, record, table or
column name appears in any pattern.

Every fact is OPTIONAL. A value that cannot be found is 0, empty or
None, and never raises.
"""

from __future__ import annotations

import re

# ------------------------------------------------------------ counts
MAPPING_ROWS = re.compile(
    r"Sheet\s+Mapping\s+(?:rows|Rows)\s*[:=]\s*(?P<count>\d+)", re.IGNORECASE
)
DCLGEN_COLUMNS = re.compile(
    r"DCLGEN\s+(?:total\s+)?columns\s*[:=]\s*(?P<count>\d+)", re.IGNORECASE
)
COPYBOOK_FIELDS = re.compile(
    r"Copybook\s+(?:total\s+)?fields\s*[:=]\s*(?P<count>\d+)", re.IGNORECASE
)
LRF_RECORDS = re.compile(
    r"LRF\s+logical\s+records\s+parsed\s*[:=]\s*(?P<count>\d+)", re.IGNORECASE
)

# --------------------------------------------------------- artefacts
OUTPUT_FILE = re.compile(
    r"Output\s+file\s+created\s*[:=]\s*(?P<path>.+)$",
    re.IGNORECASE | re.MULTILINE,
)
REVIEW_SUMMARY = re.compile(
    r"Reviewed\s*[:=]\s*(?P<reviewed>\d+)\s+"
    r"Accepted\s*[:=]\s*(?P<accepted>\d+)\s+"
    r"Rejected\s*[:=]\s*(?P<rejected>\d+)",
    re.IGNORECASE,
)

# ----------------------------------------------------------- failure
# LoggerFactory format: "DD-MM-YYYY HH:MM:SS | LEVEL | name | message"
LOG_LINE = re.compile(
    r"^\s*\d{2}-\d{2}-\d{4}\s+\d{2}:\d{2}:\d{2}\s*\|\s*"
    r"(?P<level>[A-Z]+)\s*\|\s*[^|]+\|\s*(?P<message>.*)$"
)
ERROR_LINE = re.compile(r"^ERROR:\s*(?P<message>.+)$", re.IGNORECASE | re.MULTILINE)
TRACEBACK = re.compile(r"^Traceback $most recent call last$", re.MULTILINE)

# Levels worth a terminal line. INFO and DEBUG belong in the transcript.
ATTENTION_LEVELS = ("WARNING", "ERROR", "CRITICAL")

# Hard cap so one broken step cannot flood the terminal.
ATTENTION_MAX = 8


def _count(pattern: re.Pattern, text: str) -> int:
    match = pattern.search(text)
    return int(match.group("count")) if match else 0


def _attention(text: str) -> tuple[list[str], int, int]:
    """(shown, total_attention, total_messages) from the log lines."""
    shown: list[str] = []
    total = 0
    messages = 0

    for raw in text.splitlines():
        match = LOG_LINE.match(raw)
        if not match:
            continue
        messages += 1
        if match.group("level") not in ATTENTION_LEVELS:
            continue
        total += 1
        message = match.group("message").strip()
        if message and len(shown) < ATTENTION_MAX and message not in shown:
            shown.append(message)

    return shown, total, messages


def digest(text: str) -> dict:
    """Facts worth printing. Never raises, never returns None."""
    body = str(text or "")
    attention, attention_total, messages = _attention(body)
    review_match = REVIEW_SUMMARY.search(body)

    return {
        "mapping_rows": _count(MAPPING_ROWS, body),
        "dclgen_columns": _count(DCLGEN_COLUMNS, body),
        "copybook_fields": _count(COPYBOOK_FIELDS, body),
        "lrf_records": _count(LRF_RECORDS, body),
        "outputs": [m.group("path").strip() for m in OUTPUT_FILE.finditer(body)],
        "review": (
            {
                "reviewed": int(review_match.group("reviewed")),
                "accepted": int(review_match.group("accepted")),
                "rejected": int(review_match.group("rejected")),
            }
            if review_match
            else None
        ),
        "messages": messages,
        "attention": attention,
        "attention_total": attention_total,
        "errors": [m.group("message").strip() for m in ERROR_LINE.finditer(body)],
        "crashed": bool(TRACEBACK.search(body)),
    }


__all__ = ["digest"]