# LOCATION: rules/cursor_close_guarantee_rules.py
# ACTION: CREATE NEW FILE

"""Cursor close-guarantee rules.

Constants only. No regex, no runtime logic, no program / paragraph /
record / table / cursor / host variable names.

WHY THIS EXISTS
---------------
`CursorFlowComposer` handles two loop idioms (INLINE and SPAN). When a
program matches neither - as every LRF-expanded program did - it logged
`no_loop_for_cursor` as a WARNING and emitted:

    PERFORM 710-OPEN-DZBFASC1.
    PERFORM 720-FETCH-DZBFASC1.        <- primes once, never loops
    ...
    PERFORM 720-FETCH-DZBFASC1.        <- orphan repeat fetch

with `730-CLOSE-DZBFASC1` declared but never performed. The cursor is
opened, read twice and leaked. This pass is the last-resort guarantee
that produces the manual reference shape:

    PERFORM 710-OPEN-DZBFASC1.
    PERFORM 720-FETCH-DZBFASC1 UNTIL DZBFASC1-EOC.
    PERFORM 730-CLOSE-DZBFASC1.

and drives the business paragraph from the FETCH paragraph:

    EVALUATE SQLCODE
      WHEN ZERO
           PERFORM BEHANDELING THRU BEHANDELING-EXIT
"""

from __future__ import annotations

#
# Master switches
#
ENFORCE_CURSOR_CLOSE_GUARANTEE = True

# Convert a primed-but-unlooped fetch into PERFORM <fetch> UNTIL <eoc>.
SYNTHESISE_MISSING_DRIVING_LOOP = True

# Rewrite the FETCH paragraph WHEN ZERO branch to drive the business
# paragraph that used to carry the OBTAIN NEXT.
ENFORCE_FETCH_DRIVES_BUSINESS_PARAGRAPH = True

# Emit PERFORM <para> THRU <para>-EXIT when the exit paragraph exists.
PREFER_THRU_EXIT_PARAGRAPH = True

#
# Cursor paragraph operations
#
OPERATION_OPEN = "OPEN"
OPERATION_FETCH = "FETCH"
OPERATION_CLOSE = "CLOSE"
REQUIRED_OPERATIONS = (OPERATION_OPEN, OPERATION_FETCH, OPERATION_CLOSE)

#
# End-of-cursor condition
#
EOC_CONDITION_TEMPLATE = "{cursor}-EOC"

# Conditions meaning "the legacy IDMS / raw SQLCODE end test is still here".
LEGACY_EOC_CONDITIONS = (
    "SQLCODE = 100",
    "SQLCODE=100",
    "SQLCODE = +100",
    "SQLCODE=+100",
    "DB-END-OF-SET",
    "DB-REC-NOT-FOUND",
)

#
# Generated statements
#
PERFORM_FETCH_UNTIL_TEMPLATE = "PERFORM {fetch} UNTIL {condition}."
PERFORM_CLOSE_TEMPLATE = "PERFORM {close}."
PERFORM_BUSINESS_TEMPLATE = "PERFORM {paragraph}"
PERFORM_BUSINESS_THRU_TEMPLATE = "PERFORM {paragraph} THRU {through}"
UNTIL_TEMPLATE = "UNTIL {condition}"

EXIT_PARAGRAPH_SUFFIX = "-EXIT"
STATEMENT_TERMINATOR = "."

# How far ahead of a PERFORM the UNTIL clause may sit on its own line.
UNTIL_LOOKAHEAD_LIMIT = 3

# Single word lines ending in a period that are NOT paragraph headers.
NON_PARAGRAPH_SINGLE_WORDS = frozenset({
    "CONTINUE",
    "END-EXEC",
    "END-EVALUATE",
    "END-IF",
    "END-PERFORM",
    "END-READ",
    "END-SEARCH",
    "END-STRING",
    "END-WRITE",
    "EXIT",
    "GOBACK",
    "STOP",
})

#
# Diagnostics
#
CURSOR_CLOSE_GUARANTEE_MESSAGES = {
    "loop_synthesised": (
        "Cursor close guarantee: cursor {cursor} had no driving loop; "
        "emitted PERFORM {fetch} UNTIL {condition} and PERFORM {close}."
    ),
    "condition_rewritten": (
        "Cursor close guarantee: rewrote the {cursor} loop exit condition "
        "to {condition}."
    ),
    "close_inserted": (
        "Cursor close guarantee: inserted PERFORM {close} after the "
        "{cursor} driving loop."
    ),
    "close_present": (
        "Cursor close guarantee: {close} is already performed; no "
        "insertion needed."
    ),
    "business_paragraph_bound": (
        "Cursor close guarantee: FETCH paragraph {fetch} now performs "
        "business paragraph {paragraph}."
    ),
    "repeat_fetch_removed": (
        "Cursor close guarantee: removed the orphan repeat PERFORM "
        "{fetch} left by the converted OBTAIN NEXT."
    ),
    "no_open_perform": (
        "Cursor close guarantee: cursor {cursor} has OPEN/FETCH/CLOSE "
        "paragraphs but is never opened; left untouched for review."
    ),
    "incomplete_paragraph_set": (
        "Cursor close guarantee: cursor {cursor} does not have a complete "
        "OPEN/FETCH/CLOSE paragraph set; skipped."
    ),
    "business_paragraph_unknown": (
        "Cursor close guarantee: could not identify the business "
        "paragraph for cursor {cursor}; WHEN ZERO left unchanged."
    ),
}

__all__ = [
    "ENFORCE_CURSOR_CLOSE_GUARANTEE",
    "SYNTHESISE_MISSING_DRIVING_LOOP",
    "ENFORCE_FETCH_DRIVES_BUSINESS_PARAGRAPH",
    "PREFER_THRU_EXIT_PARAGRAPH",
    "OPERATION_OPEN",
    "OPERATION_FETCH",
    "OPERATION_CLOSE",
    "REQUIRED_OPERATIONS",
    "EOC_CONDITION_TEMPLATE",
    "LEGACY_EOC_CONDITIONS",
    "PERFORM_FETCH_UNTIL_TEMPLATE",
    "PERFORM_CLOSE_TEMPLATE",
    "PERFORM_BUSINESS_TEMPLATE",
    "PERFORM_BUSINESS_THRU_TEMPLATE",
    "UNTIL_TEMPLATE",
    "EXIT_PARAGRAPH_SUFFIX",
    "STATEMENT_TERMINATOR",
    "UNTIL_LOOKAHEAD_LIMIT",
    "NON_PARAGRAPH_SINGLE_WORDS",
    "CURSOR_CLOSE_GUARANTEE_MESSAGES",
]