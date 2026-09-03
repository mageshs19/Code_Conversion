from __future__ import annotations

import re

"""
Regex patterns for update main-flow postprocess.

This file contains regex patterns only.
No conversion logic, business rules, file paths, program names, DB2 table names,
DCLGEN names, copybook names, or host variables belong here.
"""

OPEN_INPUT_LINE_PATTERN = re.compile(
    r"\bOPEN\s+INPUT\s+(?P<file>[A-Z0-9-]+)\b",
    flags=re.IGNORECASE,
)

STOP_RUN_LINE_PATTERN = re.compile(
    r"\bSTOP\s+RUN\b\.?",
    flags=re.IGNORECASE,
)

PROCEDURE_DIVISION_LINE_PATTERN = re.compile(
    r"^PROCEDURE\s+DIVISION\b",
    flags=re.IGNORECASE,
)

DIVISION_LINE_PATTERN = re.compile(
    r"^[A-Z][A-Z0-9-]*\s+DIVISION\b",
    flags=re.IGNORECASE,
)

SECTION_LINE_PATTERN = re.compile(
    r"^[A-Z][A-Z0-9-]*\s+SECTION\b",
    flags=re.IGNORECASE,
)

PARAGRAPH_HEADER_LINE_PATTERN = re.compile(
    r"^[A-Z0-9][A-Z0-9-]*\.$",
    flags=re.IGNORECASE,
)

PERFORM_UNTIL_LINE_PATTERN = re.compile(
    r"\bPERFORM\s+(?P<paragraph>[A-Z0-9][A-Z0-9-]*)\s+UNTIL\b",
    flags=re.IGNORECASE,
)

PERFORM_READ_FLAT_FILE_LINE_PATTERN = re.compile(
    r"^PERFORM\s+READ-FLAT-FILE\.?$",
    flags=re.IGNORECASE,
)

EXEC_SQL_LINE_PATTERN = re.compile(
    r"\bEXEC\s+SQL\b",
    flags=re.IGNORECASE,
)

MOVE_LINE_PATTERN = re.compile(
    r"^MOVE\b",
    flags=re.IGNORECASE,
)

PERFORM_LINE_PATTERN = re.compile(
    r"^PERFORM\b",
    flags=re.IGNORECASE,
)