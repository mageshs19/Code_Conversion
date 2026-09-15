# LOCATION: rules/fixed_format_wrap_rules.py
# ACTION: CREATE NEW FILE

"""
Fixed-format statement wrapping rules.

Constants only. No regex, no runtime logic, no program, record, table,
DCLGEN, or host variable names.

A rewritten statement that no longer fits columns 8-72 must be WRAPPED,
never truncated and never silently skipped. Truncation produces an
undefined data name and fails compilation; skipping leaves an unqualified
reference that fails DB2 precompilation.
"""

from __future__ import annotations

# Fixed-format geometry.
BODY_START_COLUMN = 8
BODY_END_COLUMN = 72
BODY_WIDTH = 65                 # columns 8-72 inclusive

# Continuation indent applied to wrapped fragments.
CONTINUATION_INDENT = "   "

# Statement tokens used by the MOVE splitter.
TOKEN_MOVE = "MOVE"
TOKEN_TO = "TO"
TOKEN_OF_DCL = " OF DCL"

# COBOL sentence terminator.
PERIOD = "."

# Statements that legitimately end a sentence and may carry the period.
SENTENCE_TERMINATORS = (
    "END-IF",
    "END-EVALUATE",
    "END-PERFORM",
    "END-READ",
    "END-WRITE",
    "END-EXEC",
    "CONTINUE",
)

# Diagnostics.
DIAG_WRAPPED_TEMPLATE = (
    "Fixed format: wrapped rewritten statement that exceeded column "
    "{column}."
)
DIAG_PERIOD_RESTORED = (
    "Fixed format: restored sentence terminator lost when an enclosing "
    "block was removed."
)