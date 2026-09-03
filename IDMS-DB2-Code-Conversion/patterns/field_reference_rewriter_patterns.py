from __future__ import annotations

"""
Regex patterns for field reference rewriting.

This module contains regex patterns only.
"""

import re


QUALIFIED_REFERENCE_PATTERN = re.compile(
    r"\b(?P<field>[A-Z][A-Z0-9-]*)\s+"
    r"(?P<qualifier>OF|IN)\s+"
    r"(?P<record>[A-Z][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)


EXEC_SQL_PATTERN = re.compile(
    r"^\s*EXEC\s+SQL\b",
    flags=re.IGNORECASE,
)


END_EXEC_PATTERN = re.compile(
    r"^\s*END-EXEC\.?\s*$",
    flags=re.IGNORECASE,
)


DIVISION_PATTERN = re.compile(
    r"^\s*(IDENTIFICATION|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION\b",
    flags=re.IGNORECASE,
)


PARAGRAPH_PATTERN = re.compile(
    r"^\s*(?P<name>[A-Z0-9][A-Z0-9-]*)\.\s*$",
    flags=re.IGNORECASE,
)


STRING_PATTERN = re.compile(
    r"'[^']*'",
    flags=re.IGNORECASE,
)


HOST_REFERENCE_OF_PATTERN = re.compile(
    r":?\s*(?P<host>[A-Z][A-Z0-9-]*)\s+OF\s+(?P<group>DCL[A-Z0-9-]+)",
    flags=re.IGNORECASE,
)


HOST_REFERENCE_DOT_PATTERN = re.compile(
    r":?\s*(?P<group>DCL[A-Z0-9-]+)\.(?P<host>[A-Z][A-Z0-9-]*)",
    flags=re.IGNORECASE,
)


INITIALIZE_DCL_PATTERN = re.compile(
    r"\bINITIALIZE\s+(?P<group>DCL[A-Z0-9-]+)\b",
    flags=re.IGNORECASE,
)


GENERATED_OBTAIN_COMMENT_PATTERN = re.compile(
    r"CONVERTED\s+(?:OBTAIN|FIND)\s+(?:FIRST|NEXT|CALC)?\s*"
    r"(?P<record>[A-Z][A-Z0-9-]*)",
    flags=re.IGNORECASE,
)


MOVE_SPACES_TO_RECORD_PATTERN = re.compile(
    r"\bMOVE\s+(?:SPACE|SPACES|ZEROES|ZEROS)\s+TO\s+"
    r"(?P<record>[A-Z][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)


LEVEL_NUMBER_FIELD_PATTERN = re.compile(
    r"^\s*(0[1-9]|[1-4][0-9]|66|77|88)\s+([A-Z][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)


REDEFINES_FIELD_PATTERN = re.compile(
    r"^\s*([A-Z][A-Z0-9-]*)\s+REDEFINES\s+[A-Z][A-Z0-9-]*",
    flags=re.IGNORECASE,
)


REDEFINES_BASE_PATTERN = re.compile(
    r"\bREDEFINES\s+([A-Z][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)


COBOL_IDENTIFIER_PATTERN = re.compile(
    r"[A-Z][A-Z0-9-]*",
    flags=re.IGNORECASE,
)


OF_IN_BEFORE_PATTERN = re.compile(
    r"\b(OF|IN)\s*$",
    flags=re.IGNORECASE,
)


OF_IN_AFTER_PATTERN = re.compile(
    r"^\s+(OF|IN)\s+[A-Z0-9-]+",
    flags=re.IGNORECASE,
)


DCL_DOT_REFERENCE_PATTERN = re.compile(
    r":\s*DCL[A-Z0-9-]+\.",
    flags=re.IGNORECASE,
)


HOST_OF_DCL_REFERENCE_PATTERN = re.compile(
    r":\s*[A-Z0-9-]+\s+OF\s+DCL[A-Z0-9-]+",
    flags=re.IGNORECASE,
)

# Splits a cleaned host reference "HOST OF GROUP" on the OF keyword.
# Used by the host-reference resolver so no regex lives in logic.
HOST_REFERENCE_OF_SPLIT_PATTERN = re.compile(
    r"\s+OF\s+",
    flags=re.IGNORECASE,
)