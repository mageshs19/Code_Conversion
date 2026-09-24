# LOCATION: rules/cursor_loop_rules.py
# ACTION: CREATE NEW FILE
"""Cursor driving-loop rules.

Constants only. No regex, no runtime logic, no program / paragraph /
record / table / cursor / host variable names.

WHY THIS EXISTS
---------------
rules/cursor_flow_rules.py describes ONE loop idiom:

    PERFORM 710-OPEN-<cursor>.
    PERFORM 720-FETCH-<cursor>.
    PERFORM <business>
        UNTIL SQLCODE = 100.

Older programs - and every LRF program, which predates that convention -
drive the loop with a paragraph span:

    PERFORM <business> THRU <business>-EXIT
        UNTIL LR-STATUS = 'VMBFAS-EOA'.

with the OPEN and the priming FETCH in a DIFFERENT paragraph, which may
appear BEFORE or AFTER the loop in source order.

Restructuring a span loop would rewrite working business flow, which the
business-flow rule forbids. The SPAN strategy is therefore deliberately
conservative: it fixes the exit condition and guarantees the cursor is
closed, and changes nothing else.
"""

from __future__ import annotations

# ---------------------------------------------------------------- master
ENFORCE_SPAN_LOOP_REWRITE = True

# A leftover OBTAIN NEXT may only be stripped when the loop it belonged to
# was ACTUALLY converted. Stripping it without a plan deletes the only
# FETCH inside the loop and the program never advances.
REQUIRE_PLAN_FOR_OBTAIN_NEXT_CLEANUP = True

# ----------------------------------------------------------- loop kinds
LOOP_KIND_INLINE = "INLINE"   # PERFORM <para> [UNTIL ...]
LOOP_KIND_SPAN = "SPAN"       # PERFORM <para> THRU <para> [UNTIL ...]

# --------------------------------------------------------- correlation
# Whole program is searched in BOTH directions. A span loop legitimately
# precedes the paragraph that opens the cursor.
SEARCH_BOTH_DIRECTIONS = True

# 0 disables the distance ceiling. A ceiling only hides correlation bugs.
MAX_CORRELATION_DISTANCE = 0

# Window used when checking whether a CLOSE is already performed.
CLOSE_PRESENCE_WINDOW = 40

# ------------------------------------------------------ exit conditions
# Conditions that mean "the legacy end test is still in place".
LEGACY_EOC_CONDITIONS = (
    "SQLCODE = 100",
    "SQLCODE=100",
    "DB-END-OF-SET",
    "DB-REC-NOT-FOUND",
)

EOC_CONDITION_TEMPLATE = "{cursor}-EOC"
EOC_CONDITION_SUFFIX = "-EOC"

# ---------------------------------------------------------- statements
UNTIL_TEMPLATE = "UNTIL {condition}"
UNTIL_TERMINATED_TEMPLATE = "UNTIL {condition}."
PERFORM_CLOSE_TEMPLATE = "PERFORM {paragraph}."

STATEMENT_TERMINATOR = "."

# ---------------------------------------------------------- diagnostics
CURSOR_LOOP_MESSAGES = {
    "scanned": (
        "Cursor flow: found {inline} inline loop(s) and {span} span loop(s)."
    ),
    "span_plan": (
        "Cursor flow: correlated cursor {cursor} with span loop "
        "PERFORM {paragraph} THRU {through}."
    ),
    "condition_rewritten": (
        "Cursor flow: rewrote span loop exit condition to {condition}."
    ),
    "close_inserted": (
        "Cursor flow: inserted {paragraph} after the span loop."
    ),
    "close_present": (
        "Cursor flow: {paragraph} already performed; no insertion needed."
    ),
    "no_loop_for_cursor": (
        "Cursor flow: cursor {cursor} has no recognised driving loop; "
        "the generated OBTAIN NEXT was left in place for manual review."
    ),
    "obtain_next_retained": (
        "Cursor flow: no cursor loop was converted, so generated fetch "
        "calls were retained."
    ),
}