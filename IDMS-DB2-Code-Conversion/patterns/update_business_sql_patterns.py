from __future__ import annotations

import re

"""
Regex patterns for update-program business SQL standardization.

This module contains regex patterns only.
No conversion logic, business rules, file paths, program names, DB2 table names,
DCLGEN names, copybook names, or host variables belong here.
"""

CONVERTED_MODIFY_COMMENT_PATTERN = re.compile(
    r"^\s*\*DB2:\s*Converted\s+MODIFY\s+for\s+(?P<record>[A-Z0-9-]+)\.?\s*$",
    flags=re.IGNORECASE,
)

SQL_LOCATION_UPDATE_PATTERN = re.compile(
    r"^\s*MOVE\s+['\"]UPDATE-(?P<record>[A-Z0-9-]+)['\"]\s+TO\s+SQL-LOCATION\s*\.?",
    flags=re.IGNORECASE,
)

EXEC_SQL_START_PATTERN = re.compile(
    r"^\s*EXEC\s+SQL\b",
    flags=re.IGNORECASE,
)

EXEC_SQL_UPDATE_PATTERN = re.compile(
    r"^\s*UPDATE\s+(?P<table>[A-Z0-9_]+)\b",
    flags=re.IGNORECASE,
)

END_EXEC_PATTERN = re.compile(
    r"^\s*END-EXEC\s*\.?",
    flags=re.IGNORECASE,
)

EVALUATE_SQLCODE_PATTERN = re.compile(
    r"^\s*EVALUATE\s+SQLCODE\b",
    flags=re.IGNORECASE,
)

WHEN_ZERO_PATTERN = re.compile(
    r"^\s*WHEN\s+0\b",
    flags=re.IGNORECASE,
)

WHEN_OTHER_PATTERN = re.compile(
    r"^\s*WHEN\s+OTHER\b",
    flags=re.IGNORECASE,
)

CONTINUE_PATTERN = re.compile(
    r"^\s*CONTINUE\s*\.?",
    flags=re.IGNORECASE,
)

END_EVALUATE_PATTERN = re.compile(
    r"^\s*END-EVALUATE\s*\.?",
    flags=re.IGNORECASE,
)

DCL_HOST_GROUP_PATTERN = re.compile(
    r"\bDCL[A-Z0-9]+\b",
    flags=re.IGNORECASE,
)

PERFORM_UPDATE_PARAGRAPH_PATTERN = re.compile(
    r"^\s*PERFORM\s+1100-UPDATE-[A-Z0-9-]+\s*\.?",
    flags=re.IGNORECASE,
)

PERFORM_READ_FLAT_FILE_PATTERN = re.compile(
    r"^\s*PERFORM\s+READ-FLAT-FILE\s*\.?",
    flags=re.IGNORECASE,
)

PARAGRAPH_HEADER_PATTERN = re.compile(
    r"^[A-Z0-9][A-Z0-9-]*\.$",
    flags=re.IGNORECASE,
)