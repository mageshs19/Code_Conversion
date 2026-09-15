# LOCATION: patterns/cursor_paragraph_patterns.py
# ACTION: CREATE NEW FILE

"""
Cursor paragraph regex patterns.

This module contains regex patterns and pattern templates only.
No business rules, conversion rules, COBOL layout text, or hardcoded
program, record, table, cursor, or host variable names belong here.
"""

from __future__ import annotations

import re

# A PERFORM of an unnumbered cursor paragraph, e.g. PERFORM OPEN-DZBEFFC1.
#
# (?![A-Z0-9-]) prevents OPEN-CUR1 from matching inside OPEN-CUR12.
# {operation} and {cursor} are injected via .format with re.escape.
UNNUMBERED_PERFORM_PATTERN_TEMPLATE = (
    r"(?P<prefix>\bPERFORM\s+)"
    r"{operation}-{cursor}"
    r"(?![A-Z0-9-])"
    r"(?P<suffix>\.?)"
)

# A PERFORM of a numbered cursor paragraph, e.g. PERFORM 710-OPEN-DZBEFFC1.
NUMBERED_PERFORM_PATTERN_TEMPLATE = (
    r"(?P<prefix>\bPERFORM\s+)"
    r"\d{{3}}-{operation}-{cursor}"
    r"(?![A-Z0-9-])"
    r"(?P<suffix>\.?)"
)

# A PERFORM of a superseded paragraph name carried on the cursor spec.
LEGACY_PERFORM_PATTERN_TEMPLATE = (
    r"(?P<prefix>\bPERFORM\s+)"
    r"{paragraph}"
    r"(?![A-Z0-9-])"
    r"(?P<suffix>\.?)"
)

# Replacement body shared by all three PERFORM rewrites.
PERFORM_REPLACEMENT_TEMPLATE = r"\g<prefix>{paragraph}\g<suffix>"

# PERFORM SQL-ERROR with an OPTIONAL terminator.
#
# The terminator is captured so the caller can carry it through unchanged.
# Substituting a fixed "PERFORM SQLERROR." would add a period to statements
# inside EVALUATE blocks and orphan END-EVALUATE.
LEGACY_SQL_ERROR_PERFORM_PATTERN = re.compile(
    r"\bPERFORM\s+SQL-ERROR(?P<dot>\s*\.)?",
    flags=re.IGNORECASE,
)

# A SQL-ERROR paragraph header on its own fixed-format line.
# A header always ends in a period, so renaming it is safe.
LEGACY_SQL_ERROR_HEADER_PATTERN = re.compile(
    r"(?m)^(?P<indent>\s*)(?:\d{6}\s+)?SQL-ERROR\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)

LEGACY_SQL_ERROR_HEADER_REPLACEMENT = r"\g<indent>SQLERROR."