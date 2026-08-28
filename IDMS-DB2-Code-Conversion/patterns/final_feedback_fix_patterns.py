"""
Final feedback fix regex patterns.

This module contains regex patterns only.

No business rules.
No runtime logic.
No hardcoded program names, table names, fields, or cursor names.
"""

from __future__ import annotations

import re


PROGRAM_ID_PATTERN = re.compile(
    r"^\s*(?:\d{6})?\s*PROGRAM-ID\.\s+"
    r"(?P<program>[A-Z0-9-]+)\.",
    flags=re.IGNORECASE | re.MULTILINE,
)

MOVE_TO_PROGRAM_NAME_PATTERN = re.compile(
    r"(?P<prefix>\bMOVE\s+')"
    r"(?P<program>[A-Z0-9-]+)"
    r"(?P<suffix>'\s+TO\s+PROGRAM-NAME\s*\.?)",
    flags=re.IGNORECASE,
)

PROCEDURE_DIVISION_TOKEN_PATTERN = re.compile(
    r"\bPROCEDURE\s+DIVISION\b",
    flags=re.IGNORECASE,
)

DIVISION_SECTION_HEADER_PATTERN = re.compile(
    r"^(IDENTIFICATION|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION\b|"
    r"^[A-Z0-9-]+\s+SECTION\.$|"
    r"^FILE-CONTROL\.$|"
    r"^INPUT-OUTPUT\s+SECTION\.$|"
    r"^FILE\s+SECTION\.$|"
    r"^WORKING-STORAGE\s+SECTION\.$|"
    r"^LINKAGE\s+SECTION\.$",
    flags=re.IGNORECASE,
)

PARAGRAPH_HEADER_PATTERN = re.compile(
    r"^[A-Z0-9][A-Z0-9-]*\.$",
    flags=re.IGNORECASE,
)

EXEC_SQL_START_PATTERN = re.compile(
    r"^EXEC\s+SQL\b",
    flags=re.IGNORECASE,
)

END_EXEC_PATTERN = re.compile(
    r"\bEND-EXEC\b",
    flags=re.IGNORECASE,
)

DECLARE_CURSOR_PATTERN = re.compile(
    r"\bDECLARE\s+(?P<cursor>[A-Z0-9-]+)\s+CURSOR\b",
    flags=re.IGNORECASE,
)

FETCH_CURSOR_PATTERN = re.compile(
    r"\bFETCH\s+(?P<cursor>[A-Z0-9-]+)\b",
    flags=re.IGNORECASE,
)

SELECT_KEYWORD_PATTERN = re.compile(
    r"^SELECT$",
    flags=re.IGNORECASE,
)

SELECT_ITEM_PATTERN = re.compile(
    r"^\s*,?\s*(?P<column>[A-Z0-9_]+)\s*$",
    flags=re.IGNORECASE,
)

FROM_PATTERN = re.compile(
    r"\bFROM\b",
    flags=re.IGNORECASE,
)

WHERE_PATTERN = re.compile(
    r"\bWHERE\b",
    flags=re.IGNORECASE,
)

ORDER_BY_PATTERN = re.compile(
    r"\bORDER\s+BY\b",
    flags=re.IGNORECASE,
)

FOR_READ_ONLY_PATTERN = re.compile(
    r"\bFOR\s+READ\s+ONLY\b",
    flags=re.IGNORECASE,
)

HOST_REFERENCE_PATTERN = re.compile(
    r":(?P<group>DCL[A-Z0-9]+)\.(?P<host>[A-Z0-9-]+)",
    flags=re.IGNORECASE,
)

ASC_DESC_PATTERN = re.compile(
    r"\b(ASC|DESC)\b",
    flags=re.IGNORECASE,
)

SQL_NAME_TOKEN_PATTERN = re.compile(
    r"^[A-Z0-9_]+$",
    flags=re.IGNORECASE,
)

DATE_HELPER_EUR_PATTERN = re.compile(
    r"\bDA-DD-MM-CCYY\b",
    flags=re.IGNORECASE,
)

DATE_LOW_EUR_LITERAL_PATTERN = re.compile(
    r"'01\.01\.0001'",
    flags=re.IGNORECASE,
)

DATE_HIGH_EUR_LITERAL_PATTERN = re.compile(
    r"'31\.12\.9999'",
    flags=re.IGNORECASE,
)

# --- Appended: patterns previously inlined in FinalFeedbackFixComposer ---

STRING_START_PATTERN = re.compile(r"^STRING\b", flags=re.IGNORECASE)
STRING_END_PATTERN = re.compile(r"^END-STRING\.?$", flags=re.IGNORECASE)
STRING_INTO_PATTERN = re.compile(r"^INTO\b", flags=re.IGNORECASE)

PROCEDURE_DIVISION_PATTERN = re.compile(
    r"^PROCEDURE\s+DIVISION\b", flags=re.IGNORECASE
)
DIVISION_PATTERN = re.compile(
    r"^[A-Z][A-Z0-9-]*\s+DIVISION\.?$", flags=re.IGNORECASE
)
SECTION_PATTERN = re.compile(
    r"^[A-Z][A-Z0-9-]*\s+SECTION\.?$", flags=re.IGNORECASE
)
PARAGRAPH_PATTERN = re.compile(
    r"^[A-Z0-9][A-Z0-9-]*\.?$", flags=re.IGNORECASE
)

# Note: EXEC_SQL_START_PATTERN and END_EXEC_PATTERN already exist in this file.
# The composer's local EXEC_SQL_END_PATTERN (r"^END-EXEC\.?$") is renamed to
# avoid clashing with the existing END_EXEC_PATTERN (r"\bEND-EXEC\b").
EXEC_SQL_END_LINE_PATTERN = re.compile(r"^END-EXEC\.?$", flags=re.IGNORECASE)

IF_START_PATTERN = re.compile(r"^IF\s+", flags=re.IGNORECASE)
ELSE_PATTERN = re.compile(r"^ELSE\.?$", flags=re.IGNORECASE)
END_IF_PATTERN = re.compile(r"^END-IF\.?$", flags=re.IGNORECASE)
EVALUATE_START_PATTERN = re.compile(r"^EVALUATE\s+", flags=re.IGNORECASE)
WHEN_PATTERN = re.compile(r"^WHEN\s+", flags=re.IGNORECASE)
END_EVALUATE_PATTERN = re.compile(r"^END-EVALUATE\.?$", flags=re.IGNORECASE)

DB2_COLON_COMMENT_BODY_PATTERN = re.compile(r"^\*?\s*DB2:", flags=re.IGNORECASE)
DB2_SPACE_COMMENT_BODY_PATTERN = re.compile(
    r"^\*?\s*DB2\s+", flags=re.IGNORECASE
)