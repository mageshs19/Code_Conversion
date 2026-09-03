from __future__ import annotations

"""
Field usage analyzer regex patterns.

This module contains regex patterns only.
No analyzer logic or business rules belong here.
"""

import re


QUALIFIED_REFERENCE_PATTERN = re.compile(
    r"\b(?P<field>[A-Z][A-Z0-9-]*)\s+(?:OF|IN)\s+"
    r"(?P<record>[A-Z][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)


DCLGEN_OF_PATTERN = re.compile(
    r":?\s*(?P<field>[A-Z][A-Z0-9-]*)\s+OF\s+"
    r"(?P<group>DCL[A-Z0-9-]+)",
    flags=re.IGNORECASE,
)


DCLGEN_DOT_PATTERN = re.compile(
    r":?\s*(?P<group>DCL[A-Z0-9-]+)\.(?P<field>[A-Z][A-Z0-9-]*)",
    flags=re.IGNORECASE,
)


MOVE_PATTERN = re.compile(
    r"\bMOVE\s+(?P<source>.+?)\s+TO\s+(?P<target>.+?)(?:\.|$)",
    flags=re.IGNORECASE,
)


CONDITION_PATTERN = re.compile(
    r"^\s*(IF|WHEN|UNTIL|EVALUATE)\b",
    flags=re.IGNORECASE,
)


DIVISION_PATTERN = re.compile(
    r"^\s*(IDENTIFICATION|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION\b",
    flags=re.IGNORECASE,
)


COMMENT_PATTERN = re.compile(
    r"^\s*[\*/]",
    flags=re.IGNORECASE,
)


EXEC_SQL_START_PATTERN = re.compile(
    r"^EXEC\s+SQL\b",
    flags=re.IGNORECASE,
)


EXEC_SQL_END_PATTERN = re.compile(
    r"^END-EXEC\b",
    flags=re.IGNORECASE,
)