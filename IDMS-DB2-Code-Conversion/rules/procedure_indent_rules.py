# LOCATION: rules/procedure_indent_rules.py
# ACTION: CREATE NEW FILE

"""Procedure Division indentation rules.

Constants only. No regex, no runtime logic, no program / paragraph /
record / table / cursor / host variable names.

Indentation model, measured from the COBOL team's manual reference
program. All values are BODY indents, relative to column 8.

    009790     IF NOT SW-STATUS-D = 'Y'          body indent 4  (col 12)
    009800        IF WS-STATUS = 'C'             body indent 7  (col 15)
    009900           PERFORM WRITE-UITRECORD     body indent 10 (col 18)
    010100        END-IF                         body indent 7
    010101     END-IF.                           body indent 4

    011300     EXEC SQL                          body indent 4
    011400       OPEN DZBEFFC1                   body indent 6
    011500     END-EXEC                          body indent 4

    011700     EVALUATE SQLCODE                  body indent 4
    011800       WHEN ZERO                       body indent 6
    011900            SET ... TO TRUE            body indent 11
    012300     END-EVALUATE                      body indent 4
    012400     .                                 body indent 4
"""

from __future__ import annotations

# =====================================================================
# Master switch
# =====================================================================
ENFORCE_PROCEDURE_INDENT = True

# =====================================================================
# Indent geometry, relative to column 8
# =====================================================================
AREA_A_INDENT = 0          # column 8  - paragraph and section headers
AREA_B_INDENT = 4          # column 12 - statements at depth 0
NEST_STEP = 3              # each IF / inline PERFORM level

# EVALUATE offsets, relative to the EVALUATE's own indent.
WHEN_OFFSET = 2            # WHEN sits 2 past EVALUATE
WHEN_BODY_OFFSET = 7       # statements under a WHEN sit 7 past EVALUATE

# EXEC SQL body offset, relative to the EXEC SQL line's own indent.
SQL_BODY_OFFSET = 2

# A lone period closing a paragraph.
LONE_PERIOD = "."
LONE_PERIOD_INDENT = AREA_B_INDENT

# =====================================================================
# Safety limits
# =====================================================================
# Deeper than this and the depth tracker has almost certainly lost sync
# with a malformed program. Re-indenting further would do more harm than
# good, so the pass falls back to leaving lines untouched.
MAX_NESTING_DEPTH = 12

# =====================================================================
# Block classification
# =====================================================================
BLOCK_KIND_IF = "IF"
BLOCK_KIND_EVALUATE = "EVALUATE"
BLOCK_KIND_PERFORM = "PERFORM"
BLOCK_KIND_SQL = "SQL"
BLOCK_KIND_OTHER = "OTHER"

# Scope terminators mapped to the opener they close.
SCOPE_TERMINATORS = {
    "END-IF": BLOCK_KIND_IF,
    "END-EVALUATE": BLOCK_KIND_EVALUATE,
    "END-PERFORM": BLOCK_KIND_PERFORM,
    "END-EXEC": BLOCK_KIND_SQL,
    "END-READ": BLOCK_KIND_OTHER,
    "END-SEARCH": BLOCK_KIND_OTHER,
    "END-STRING": BLOCK_KIND_OTHER,
    "END-UNSTRING": BLOCK_KIND_OTHER,
    "END-WRITE": BLOCK_KIND_OTHER,
    "END-CALL": BLOCK_KIND_OTHER,
    "END-ADD": BLOCK_KIND_OTHER,
    "END-SUBTRACT": BLOCK_KIND_OTHER,
    "END-MULTIPLY": BLOCK_KIND_OTHER,
    "END-DIVIDE": BLOCK_KIND_OTHER,
    "END-COMPUTE": BLOCK_KIND_OTHER,
}

# Verbs that open an explicitly scoped block.
SCOPED_OPENERS = {
    "READ": BLOCK_KIND_OTHER,
    "SEARCH": BLOCK_KIND_OTHER,
    "STRING": BLOCK_KIND_OTHER,
    "UNSTRING": BLOCK_KIND_OTHER,
}

# Single-word lines ending in a period that are NOT paragraph headers.
NON_PARAGRAPH_SINGLE_WORDS = frozenset(
    {
        "CONTINUE", "EXIT", "GOBACK", "STOP",
        "END-IF", "END-EVALUATE", "END-PERFORM", "END-EXEC",
        "END-READ", "END-SEARCH", "END-STRING", "END-UNSTRING",
        "END-WRITE", "END-CALL", "END-ADD", "END-SUBTRACT",
        "END-MULTIPLY", "END-DIVIDE", "END-COMPUTE",
        "ELSE", "EJECT", "SKIP1", "SKIP2", "SKIP3",
    }
)

# =====================================================================
# Diagnostics
# =====================================================================
PROCEDURE_INDENT_MESSAGES = {
    "normalized": (
        "Procedure indent: normalized {count} statement line(s) to Area B."
    ),
    "wrapped": (
        "Procedure indent: wrapped {count} line(s) that no longer fit "
        "columns 8-72 after re-indenting."
    ),
    "skipped_depth": (
        "Procedure indent: nesting depth exceeded {limit} at line {line}; "
        "remaining lines left untouched."
    ),
    "skipped_unbalanced": (
        "Procedure indent: unbalanced scope terminator '{token}' in "
        "paragraph {paragraph}; block left untouched."
    ),
}

ENFORCE_AREA_ALIGNMENT_REFLOW = False