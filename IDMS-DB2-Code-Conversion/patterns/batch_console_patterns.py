# LOCATION: patterns/batch_console_patterns.py
# ACTION: REPLACE ENTIRE FILE

"""Batch console output-scraping patterns.

Patterns only. No labels, no rules, no layout constants.

The batch orchestrator launches each runner as a SUBPROCESS so that a
change inside a runner cannot break the orchestrator. Everything it
reports is therefore read back out of the runner's own console output,
using the wording those runners already emit from
rules/retrieval_runner_messages.py, rules/update_runner_messages.py and
code_review/standards/wording.py.

Every pattern is optional: a value that cannot be found renders as '-'
and never fails the batch.
"""

from __future__ import annotations

import re

# =====================================================================
# Metadata counts
# =====================================================================
MAPPING_ROWS_PATTERN = re.compile(
    r"Sheet\s+Mapping\s+rows\s*[:=]\s*(?P<count>\d+)",
    flags=re.IGNORECASE,
)

DCLGEN_COLUMNS_PATTERN = re.compile(
    r"DCLGEN\s+total\s+columns\s*[:=]\s*(?P<count>\d+)",
    flags=re.IGNORECASE,
)

COPYBOOK_FIELDS_PATTERN = re.compile(
    r"Copybook\s+total\s+fields\s*[:=]\s*(?P<count>\d+)",
    flags=re.IGNORECASE,
)

PROGRAM_COUNT_PATTERN = re.compile(
    r"Program\s+Count\s*[:=]\s*(?P<count>\d+)",
    flags=re.IGNORECASE,
)

# =====================================================================
# Artefacts
# =====================================================================
OUTPUT_FILE_PATTERN = re.compile(
    r"Output\s+file\s+created\s*[:=]\s*(?P<path>.+)$",
    flags=re.IGNORECASE | re.MULTILINE,
)

REPORT_FOLDER_PATTERN = re.compile(
    r"Reports\s+written\s+to\s*[:=]\s*(?P<path>.+)$",
    flags=re.IGNORECASE | re.MULTILINE,
)

# =====================================================================
# Verdicts
# =====================================================================
REVIEW_SUMMARY_PATTERN = re.compile(
    r"Reviewed\s*[:=]\s*(?P<reviewed>\d+)\s+"
    r"Accepted\s*[:=]\s*(?P<accepted>\d+)\s+"
    r"Rejected\s*[:=]\s*(?P<rejected>\d+)",
    flags=re.IGNORECASE,
)

# The review runners' --quiet line:
#   REJECTED  VMDZ4420_db2.cbl  blocking: CHK-02
QUIET_VERDICT_PATTERN = re.compile(
    r"^(?P<verdict>ACCEPTED|REJECTED)\s+(?P<name>\S+)(?P<rest>.*)$",
    flags=re.IGNORECASE | re.MULTILINE,
)

# The blocking check ids on that line. This is the single fact the COBOL
# team needs from a rejected review, so it is extracted explicitly rather
# than left buried in the runner's log.
BLOCKING_PATTERN = re.compile(
    r"blocking\s*[:=]\s*(?P<ids>[A-Z0-9][A-Z0-9,\s\-]*)",
    flags=re.IGNORECASE,
)

NOTHING_TO_DO_PATTERN = re.compile(
    r"Nothing\s+to\s+(convert|review)\b",
    flags=re.IGNORECASE,
)

CONVERSION_FAILED_PATTERN = re.compile(
    r"Conversion\s+failed\s*[:=]\s*(?P<names>.+)$",
    flags=re.IGNORECASE | re.MULTILINE,
)

# =====================================================================
# Log filtering
# =====================================================================
# LoggerFactory writes "%(asctime)s | %(levelname)s | %(name)s |
# %(message)s" to a StreamHandler, which defaults to stderr. Dumping the
# stderr tail therefore showed five INFO lines instead of the failure.
# This pattern lets the console keep only the levels that matter.
LOG_LINE_PATTERN = re.compile(
    r"^(?P<stamp>\d{2}-\d{2}-\d{4}\s+\d{2}:\d{2}:\d{2})\s*\|\s*"
    r"(?P<level>[A-Z]+)\s*\|\s*"
    r"(?P<logger>[^|]+?)\s*\|\s*"
    r"(?P<message>.*)$"
)

ERROR_LINE_PATTERN = re.compile(
    r"^ERROR:\s*(?P<message>.+)$",
    flags=re.IGNORECASE | re.MULTILINE,
)

TRACEBACK_PATTERN = re.compile(
    r"^(?P<line>\s*(Traceback $most recent call last$|\w+Error:|\w+Exception:).*)$",
    flags=re.MULTILINE,
)