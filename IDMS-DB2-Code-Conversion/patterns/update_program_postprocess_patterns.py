"""
Regex patterns for update-program postprocess conversion.

This module contains regex patterns only.
No conversion logic, business decisions, or hardcoded program-specific values
belong here.
"""

from __future__ import annotations

import re


WORKING_STORAGE_SECTION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?WORKING-STORAGE\s+SECTION\s*\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

LINKAGE_SECTION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?LINKAGE\s+SECTION\s*\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

PROCEDURE_DIVISION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?PROCEDURE\s+DIVISION\b.*?\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

END_PROGRAM_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?END\s+PROGRAM\s+[A-Z0-9_-]+\s*\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

READ_FLAT_FILE_HEADER_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?READ-FLAT-FILE\s*\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)

PARAGRAPH_HEADER_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?[A-Z0-9][A-Z0-9-]*\s*\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)

COPY_INCLUDE_TOKEN_PATTERN_TEMPLATE = r"\bCOPY\s+{include_name}\s*\."

EXEC_SQL_INCLUDE_TOKEN_PATTERN_TEMPLATE = (
    r"\bEXEC\s+SQL\s+INCLUDE\s+{include_name}\s+END-EXEC\s*\."
)

MALFORMED_SQLERROR_END_EVALUATE_PATTERN = re.compile(
    r"\bPERFORM\s+SQLERROR\s*\.\s*END-EVALUATE\b",
    flags=re.IGNORECASE,
)

OLD_EOF_EQUALS_Y_PATTERN = re.compile(
    r"\b(?P<switch>[A-Z][A-Z0-9-]*)\s*=\s*['\"]Y['\"]",
    flags=re.IGNORECASE,
)

MOVE_Y_TO_EOF_PATTERN = re.compile(
    r"\bMOVE\s+['\"]Y['\"]\s+TO\s+(?P<switch>[A-Z][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)

MOVE_N_TO_EOF_PATTERN = re.compile(
    r"\bMOVE\s+['\"]N['\"]\s+TO\s+(?P<switch>[A-Z][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)

OPEN_INPUT_PATTERN = re.compile(
    r"\bOPEN\s+INPUT\s+(?P<file>[A-Z0-9-]+)\b",
    flags=re.IGNORECASE,
)

PERFORM_UNTIL_EOF_PATTERN = re.compile(
    r"\bPERFORM\s+(?P<paragraph>[A-Z0-9-]+)\s+UNTIL\s+"
    r"(?P<switch>[A-Z0-9-]+)\s*=\s*['\"]Y['\"]",
    flags=re.IGNORECASE,
)

OLD_RESTART_RECORD_REFERENCE_PATTERN = re.compile(
    r"\b(?:OF|IN)\s+(?P<record>[A-Z0-9-]+)\b",
    flags=re.IGNORECASE,
)