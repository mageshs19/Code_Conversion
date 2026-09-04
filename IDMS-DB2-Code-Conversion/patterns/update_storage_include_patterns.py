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

# --- Legacy IDMS abend/checkpoint marker removal (generic, by '##&&' prefix) ---
# These 77-level markers (e.g. STOP01 VALUE '##&&...') are IDMS-era abend
# labels with no DB2 meaning. Detected by the '##&&' literal prefix, never by
# a hardcoded program-specific field name.

# A 77-level header that declares only a PIC X(nn) with NO inline VALUE.
# (Wrapped case: the VALUE lives on the following line.)


# APPEND to rules/update_restart_rules.py
LEGACY_ABEND_MARKER_LITERAL_PREFIX = "##&&"


# APPEND to patterns/update_storage_include_patterns.py
LEGACY_ABEND_MARKER_77_ONELINE_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?77\s+[A-Z0-9-]+\s+PIC\s+X$\d+$\s+"
    r"VALUE\s+'##&&[^']*'\s*\.?\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)
LEGACY_ABEND_MARKER_VALUE_LINE_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?VALUE\s+'##&&[^']*'\s*\.?\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)
LEGACY_ABEND_MARKER_77_HEADER_NO_VALUE_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?77\s+[A-Z0-9-]+\s+PIC\s+X$\d+$\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)
LEGACY_ABEND_MARKER_77_HEADER_NAMED_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?77\s+(?P<name>[A-Z0-9-]+)\s+PIC\s+X$\d+$\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)