# LOCATION: rules/structural_safety_rules.py
# ACTION: REPLACE ENTIRE FILE
"""Structural safety rules for generated COBOL.

Constants only. No regex, no runtime logic, no program / paragraph /
record / table / cursor / host variable names.

WHY THIS EXISTS
---------------
Three passes move or insert lines: the output-write extraction, the
counter declaration and the layout composer. Each was written against one
program shape. On an older program they produced source the compiler
rejects:

  A1. an IF whose CONDITION spans lines was split across two paragraphs,
  A2. a whole-record MOVE survived after the record's copybook was
      removed, leaving an undefined data-name,
  A4. a duplicate statement was left after a paragraph EXIT, unreachable
      and outside any paragraph,
  A5. a counter was declared INSIDE the 01 output record, shifting every
      byte of a fixed-length record.

Every rule here makes a pass REFUSE rather than guess. Refusing leaves
working COBOL and a diagnostic; guessing produces source that will not
compile.
"""

from __future__ import annotations

# =====================================================================
# A1 - condition integrity
# =====================================================================
# An extraction must never cut between the IF keyword and the end of its
# condition. Multi-line conditions are normal in hand-written COBOL.
ENFORCE_CONDITION_INTEGRITY = True

# Lines scanned forward looking for the end of a condition.
CONDITION_SCAN_LIMIT = 24

# Tokens that continue a condition onto the next line.
CONDITION_CONTINUATION_TOKENS = (
    "AND",
    "OR",
    "NOT",
)

# A statement verb proves the condition has ended.
CONDITION_TERMINATING_VERBS = (
    "ACCEPT", "ADD", "CALL", "CLOSE", "COMPUTE", "CONTINUE", "DELETE",
    "DISPLAY", "DIVIDE", "ELSE", "END-IF", "EVALUATE", "EXEC", "EXIT",
    "GO", "GOBACK", "IF", "INITIALIZE", "INSPECT", "MOVE", "MULTIPLY",
    "OPEN", "PERFORM", "READ", "RETURN", "REWRITE", "SEARCH", "SET",
    "STOP", "STRING", "SUBTRACT", "UNSTRING", "WRITE",
)

# =====================================================================
# A2 - orphaned whole-record references
# =====================================================================
ENFORCE_ORPHANED_RECORD_GUARD = True

ORPHANED_RECORD_MARKER_TEMPLATE = (
    "*DB2-KEEP: {record} is an IDMS record with no DB2 layout after "
    "conversion - re-map this reference manually."
)
ORPHANED_LINE_PREFIX = "*DB2-KEEP "

# =====================================================================
# A4 - unreachable statements
# =====================================================================
ENFORCE_UNREACHABLE_STATEMENT_GUARD = True

UNREACHABLE_MARKER = (
    "*DB2-KEEP: statement follows a paragraph EXIT and is unreachable."
)

PARAGRAPH_EXIT_WORDS = (
    "EXIT",
    "GOBACK",
    "STOP RUN",
)

# ---- blast radius cap
#
# Real unreachable code after a paragraph EXIT is one or two stray lines.
# A guard that fires dozens of times has lost sync with the paragraph
# structure - a converter defect, not a program defect. When the cap is
# exceeded the WHOLE pass is reverted and reported, so a tracking bug can
# never comment out working code.
MAX_UNREACHABLE_STATEMENTS = 3

# =====================================================================
# A5 - counter group placement
# =====================================================================
# A counter may only join an existing 01 group when that group is provably
# a work area. Anything written, read into, or moved as a whole is a
# record layout and must never gain a field.
ENFORCE_SAFE_COUNTER_GROUP = True

# Reusing a business group is technically safe but semantically noisy:
# a row counter inside 01 WS-DATUMS reads as a date field. The generated
# group is deterministic and reviewable, so it is preferred outright.
PREFER_GENERATED_COUNTER_GROUP = True

GENERATED_COUNTER_GROUP_NAME = "WS-DB2-COUNTERS"
GENERATED_COUNTER_GROUP_TEMPLATE = "01  {name}."
GENERATED_COUNTER_GROUP_MARKER = "DB2 GENERATED ROW COUNTERS"

# Body indent for children of a generated 01 group.
# 4 spaces from column 8 lands the level number in Area B (column 12).
GENERATED_COUNTER_CHILD_INDENT = "    "

# Verbs that prove an 01 group is a record layout, not a work area.
RECORD_LAYOUT_VERBS = (
    "WRITE",
    "READ",
    "REWRITE",
    "RELEASE",
    "RETURN",
)

# =====================================================================
# Diagnostics
# =====================================================================
STRUCTURAL_SAFETY_MESSAGES = {
    # ---- A1
    "extraction_refused": (
        "Structural safety: output write extraction refused - the guard "
        "condition spans {count} lines and cannot be split."
    ),
    # ---- A2
    "orphaned_record_commented": (
        "Structural safety: commented whole-record reference to {record}; "
        "the IDMS layout no longer exists."
    ),
    # ---- A4
    "unreachable_commented": (
        "Structural safety: commented {count} unreachable statement(s) "
        "after a paragraph EXIT."
    ),
    "unreachable_aborted": (
        "Structural safety: unreachable-statement guard matched {count} "
        "lines, above the limit of {limit}; the pass was reverted and no "
        "line was commented."
    ),
    # ---- A5
    "counter_group_created": (
        "Structural safety: created {group} for generated row counters."
    ),
    "counter_group_reused": (
        "Structural safety: reused work group {group} for row counters."
    ),
    "counter_group_rejected": (
        "Structural safety: {group} is a record layout; counters were not "
        "declared inside it."
    ),
}