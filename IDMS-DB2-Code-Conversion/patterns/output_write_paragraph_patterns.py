# LOCATION: patterns/output_write_paragraph_patterns.py
# ACTION: CREATE NEW FILE

"""Output write paragraph extraction regex patterns.

This file must contain regex patterns only.

No token lists, business rules, conversion rules or layout constants.
All patterns are matched against an already-stripped logical line
(sequence numbers and indicator removed, uppercased).
"""

from __future__ import annotations

import re

# A paragraph header on a stripped logical line.
PARAGRAPH_HEADER_PATTERN = re.compile(
    r"^(?P<name>[A-Z0-9][A-Z0-9-]*)\.$",
    flags=re.IGNORECASE,
)

PROCEDURE_DIVISION_PATTERN = re.compile(
    r"^PROCEDURE\s+DIVISION\b",
    flags=re.IGNORECASE,
)

DIVISION_PATTERN = re.compile(
    r"^(IDENTIFICATION|ENVIRONMENT|DATA)\s+DIVISION\b",
    flags=re.IGNORECASE,
)

# Block scope.
IF_START_PATTERN = re.compile(
    r"^IF\b",
    flags=re.IGNORECASE,
)

END_IF_PATTERN = re.compile(
    r"^END-IF\.?$",
    flags=re.IGNORECASE,
)

# The statement that identifies an output write block, and the record
# name it writes. The record name drives the generated paragraph name.
WRITE_STATEMENT_PATTERN = re.compile(
    r"^WRITE\s+(?P<record>[A-Z0-9][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)

# A PERFORM of an already generated write paragraph, used to make the
# pass idempotent.
PERFORM_WRITE_PARAGRAPH_PATTERN = re.compile(
    r"^PERFORM\s+WRITE-[A-Z0-9][A-Z0-9-]*\b",
    flags=re.IGNORECASE,
)