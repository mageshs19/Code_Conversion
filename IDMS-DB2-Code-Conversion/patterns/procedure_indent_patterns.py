# LOCATION: patterns/procedure_indent_patterns.py
# ACTION: CREATE NEW FILE

"""Procedure Division indentation regex patterns.

This file must contain regex patterns only.

No token lists, business rules, conversion rules or layout constants.
Every pattern is matched against an already-stripped, uppercased logical
line (sequence numbers and indicator removed).
"""

from __future__ import annotations

import re

# =====================================================================
# Division and section boundaries
# =====================================================================
PROCEDURE_DIVISION_PATTERN = re.compile(
    r"^PROCEDURE\s+DIVISION\b",
    flags=re.IGNORECASE,
)

OTHER_DIVISION_PATTERN = re.compile(
    r"^(IDENTIFICATION|ENVIRONMENT|DATA)\s+DIVISION\b",
    flags=re.IGNORECASE,
)

SECTION_HEADER_PATTERN = re.compile(
    r"^[A-Z0-9][A-Z0-9-]*\s+SECTION\s*\.?$",
    flags=re.IGNORECASE,
)

PARAGRAPH_HEADER_PATTERN = re.compile(
    r"^(?P<name>[A-Z0-9][A-Z0-9-]*)\.$",
    flags=re.IGNORECASE,
)

# =====================================================================
# Block openers
# =====================================================================
IF_START_PATTERN = re.compile(
    r"^IF\b",
    flags=re.IGNORECASE,
)

ELSE_PATTERN = re.compile(
    r"^ELSE\b",
    flags=re.IGNORECASE,
)

EVALUATE_START_PATTERN = re.compile(
    r"^EVALUATE\b",
    flags=re.IGNORECASE,
)

WHEN_PATTERN = re.compile(
    r"^WHEN\b",
    flags=re.IGNORECASE,
)

# An inline PERFORM block: bare PERFORM, PERFORM UNTIL, PERFORM VARYING.
# 'PERFORM paragraph-name' does NOT open a block.
INLINE_PERFORM_PATTERN = re.compile(
    r"^PERFORM\s*$"
    r"|^PERFORM\s+UNTIL\b"
    r"|^PERFORM\s+VARYING\b"
    r"|^PERFORM\s+WITH\s+TEST\b",
    flags=re.IGNORECASE,
)

SCOPED_OPENER_PATTERN = re.compile(
    r"^(?P<verb>READ|SEARCH|STRING|UNSTRING)\b",
    flags=re.IGNORECASE,
)

# =====================================================================
# Block closers
# =====================================================================
SCOPE_TERMINATOR_PATTERN = re.compile(
    r"^(?P<token>END-[A-Z]+)\s*\.?$",
    flags=re.IGNORECASE,
)

# =====================================================================
# Embedded SQL
# =====================================================================
EXEC_SQL_START_PATTERN = re.compile(
    r"^EXEC\s+SQL\b",
    flags=re.IGNORECASE,
)

END_EXEC_PATTERN = re.compile(
    r"^END-EXEC\s*\.?$",
    flags=re.IGNORECASE,
)

# =====================================================================
# Sentence terminator
# =====================================================================
LONE_PERIOD_PATTERN = re.compile(
    r"^\.$",
)