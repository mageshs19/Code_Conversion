from __future__ import annotations

import re

"""
Regex patterns for update-program storage/include cleanup.

This file contains regex patterns only.
No business rules, conversion rules, paths, program names, table names,
DCLGEN names, copybook names, or host variables belong here.
"""

PROGRAM_NAME_MOVE_PATTERN = re.compile(
    r"\bMOVE\s+['\"](?P<program>[A-Z0-9-]+)['\"]\s+TO\s+PROGRAM-NAME\s*\.?",
    flags=re.IGNORECASE,
)

CS_PROGRAM_01_PATTERN = re.compile(
    r"^(?P<prefix>\s*)(?:01)\s+CS-PROGRAM\s+PIC\s+X$8$\s+VALUE\s+"
    r"(?P<quote>['\"])(?P<value>[A-Z0-9-]+)(?P=quote)\s*\.?\s*$",
    flags=re.IGNORECASE,
)

DCL_HOST_REFERENCE_PATTERN = re.compile(
    r"(?:[:.]|\bOF\s+|\bIN\s+)\s*(?P<group>DCL[A-Z0-9]+)\b",
    flags=re.IGNORECASE,
)

EXEC_SQL_INCLUDE_PATTERN = re.compile(
    r"\bEXEC\s+SQL\s+INCLUDE\s+(?P<include>[A-Z0-9]+)\s+END-EXEC\b",
    flags=re.IGNORECASE,
)

LEGACY_77_DECLARATION_PATTERN_TEMPLATE = (
    r"^\s*(?:\d{{6}}\s*)?77\s+{name}\b.*$"
)

WORKING_STORAGE_SECTION_LINE_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?WORKING-STORAGE\s+SECTION\s*\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)

LINKAGE_SECTION_LINE_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?LINKAGE\s+SECTION\s*\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)

PROCEDURE_DIVISION_LINE_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?PROCEDURE\s+DIVISION\b.*\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)