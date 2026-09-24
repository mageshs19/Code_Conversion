# LOCATION: patterns/cursor_close_guarantee_patterns.py
# ACTION: REPLACE ENTIRE FILE

"""Regex for the cursor close-guarantee pass.

Regex only. No rules, no constants, no names, and - deliberately - NO
project import of any kind.

CORRECTION - circular import
-----------------------------
This module previously re-used patterns from a sibling pattern module.
The sibling imported back, so the first consumer to request a name while
this module was still executing failed with

    ImportError: cannot import name 'CONTINUE_PATTERN' from partially
    initialized module 'patterns.cursor_close_guarantee_patterns'

The defect was latent for as long as CursorCloseGuaranteeComposer was
never constructed. Registering the composer made the path live and the
cycle immediate. `import re` is the ONLY import this file may ever hold.

A COBOL paragraph name may begin with a DIGIT: every generated cursor
paragraph is numbered (710-OPEN-<cursor>). A pattern requiring a leading
letter makes the whole generated block invisible.
"""

from __future__ import annotations

import re

_NAME = r"[A-Z0-9][A-Z0-9-]*"

# ---- paragraph structure
PARAGRAPH_HEADER_PATTERN = re.compile(
    rf"^(?P<name>{_NAME})\s*\.\s*$",
    flags=re.IGNORECASE,
)

SECTION_HEADER_PATTERN = re.compile(
    rf"^(?P<name>{_NAME})\s+SECTION\s*\.\s*$",
    flags=re.IGNORECASE,
)

# 710-OPEN-DZBFASC1.  /  720-FETCH-DZBFASC1.  /  730-CLOSE-DZBFASC1.
CURSOR_PARAGRAPH_HEADER_PATTERN = re.compile(
    rf"^(?P<number>\d{{3,6}})-"
    rf"(?P<operation>OPEN|FETCH|CLOSE)-"
    rf"(?P<cursor>{_NAME})\s*\.\s*$",
    flags=re.IGNORECASE,
)

# ---- PERFORM statements
#
# The tail is CAPTURED, not matched, so CursorPerform.has_until can test
# it without a second pattern:
#   PERFORM 720-FETCH-C1.                  -> tail ""
#   PERFORM 720-FETCH-C1 UNTIL C1-EOC.     -> tail " UNTIL C1-EOC."
PERFORM_CURSOR_PARAGRAPH_PATTERN = re.compile(
    rf"^PERFORM\s+(?P<number>\d{{3,6}})-"
    rf"(?P<operation>OPEN|FETCH|CLOSE)-"
    rf"(?P<cursor>{_NAME})"
    rf"(?P<tail>.*)$",
    flags=re.IGNORECASE,
)

PERFORM_PARAGRAPH_PATTERN = re.compile(
    rf"^PERFORM\s+(?P<paragraph>{_NAME})\s*(?P<terminator>\.?)\s*$",
    flags=re.IGNORECASE,
)

PERFORM_INLINE_WITH_UNTIL_PATTERN = re.compile(
    rf"^PERFORM\s+(?P<paragraph>{_NAME})\s+UNTIL\s+"
    rf"(?P<condition>.+?)\s*(?P<terminator>\.?)\s*$",
    flags=re.IGNORECASE,
)

PERFORM_SPAN_PATTERN = re.compile(
    rf"^PERFORM\s+(?P<paragraph>{_NAME})\s+(?:THRU|THROUGH)\s+"
    rf"(?P<through>{_NAME})\s*(?P<terminator>\.?)\s*$",
    flags=re.IGNORECASE,
)

PERFORM_SPAN_WITH_UNTIL_PATTERN = re.compile(
    rf"^PERFORM\s+(?P<paragraph>{_NAME})\s+(?:THRU|THROUGH)\s+"
    rf"(?P<through>{_NAME})\s+UNTIL\s+"
    rf"(?P<condition>.+?)\s*(?P<terminator>\.?)\s*$",
    flags=re.IGNORECASE,
)

UNTIL_ONLY_PATTERN = re.compile(
    r"^UNTIL\s+(?P<condition>.+?)\s*(?P<terminator>\.?)\s*$",
    flags=re.IGNORECASE,
)

# ---- FETCH paragraph EVALUATE branches
WHEN_ZERO_PATTERN = re.compile(
    r"^WHEN\s+(?:ZERO|ZEROES|ZEROS|0)\s*$",
    flags=re.IGNORECASE,
)

CONTINUE_PATTERN = re.compile(
    r"^CONTINUE\s*\.?\s*$",
    flags=re.IGNORECASE,
)