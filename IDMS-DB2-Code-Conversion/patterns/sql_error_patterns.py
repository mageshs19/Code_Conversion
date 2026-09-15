# LOCATION: patterns/sql_error_patterns.py
# ACTION: CREATE NEW FILE
"""SQLERROR regex patterns.

This file must contain regex patterns only.
No token lists, business rules, conversion rules or layout constants.
"""

from __future__ import annotations

import re

# A SQLERROR or SQL-ERROR paragraph header anywhere in the text.
SQLERROR_PARAGRAPH_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?(?:SQL-ERROR|SQLERROR)\s*\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

# The same header matched against an already-stripped logical line.
SQLERROR_HEADER_ONLY_PATTERN = re.compile(
    r"(?:SQL-ERROR|SQLERROR)\s*\.",
    flags=re.IGNORECASE,
)

# Any single-word paragraph header on a stripped logical line.
PARAGRAPH_HEADER_PATTERN = re.compile(
    r"[A-Z0-9][A-Z0-9-]*\s*\.",
    flags=re.IGNORECASE,
)

# END PROGRAM on a stripped logical line.
END_PROGRAM_BOUNDARY_PATTERN = re.compile(
    r"END\s+PROGRAM\b",
    flags=re.IGNORECASE,
)