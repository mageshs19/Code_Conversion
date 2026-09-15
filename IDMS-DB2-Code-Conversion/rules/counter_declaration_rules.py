# LOCATION: rules/counter_declaration_rules.py
# ACTION: CREATE NEW FILE

"""Row counter declaration rules.

Closes open decision D-2 (processing counters) in favour of AUTOMATE,
per the COBOL team's manual reference program:

    10  WS-NB-BEFF-COUNT         PIC 9(7)    COMP-3 VALUE ZEROES.
    10  WS-NB-OUTPUT-COUNT       PIC 9(7)    COMP-3 VALUE ZEROES.
    ...
    DISPLAY 'TOTAL BEFF RECORDS   : ' WS-NB-BEFF-COUNT
    DISPLAY 'TOTAL OUTPUT RECORDS : ' WS-NB-OUTPUT-COUNT

Declaration is REFERENCE-DRIVEN, not table-driven: the composer declares
exactly the counters the PROCEDURE DIVISION actually increments. It can
therefore never declare an unused field, and never miss one.

Constants only. No regex, no runtime logic, no program / record / table /
cursor / host variable names.
"""

from __future__ import annotations

# =====================================================================
# Master switch
# =====================================================================
ENFORCE_COUNTER_DECLARATION = True

# =====================================================================
# Declaration layout
# =====================================================================
# The manual reference declares counters as subordinates of the existing
# 01 work group, at the same level as its other children. The composer
# reads that level from the group rather than assuming one.
COUNTER_DECLARATION_TEMPLATE = "{level}  {name:<24} {picture}"
COUNTER_PICTURE = "PIC 9(7)    COMP-3 VALUE ZEROES."
FALLBACK_CHILD_LEVEL = "10"

# =====================================================================
# End-of-run totals
# =====================================================================
EMIT_COUNTER_TOTALS = True

COUNTER_DISPLAY_TEMPLATE = "DISPLAY '{label} : ' {name}"
COUNTER_LABEL_TEMPLATE = "TOTAL {token} RECORDS"
COUNTER_LABEL_WIDTH = 20

# Totals are emitted immediately before the program terminates.
TOTALS_ANCHOR_STATEMENT = "STOP RUN"
TOTALS_INDENT = "    "

# =====================================================================
# Diagnostics
# =====================================================================
COUNTER_DECLARATION_MESSAGES = {
    "declared": (
        "Counters: declared {name} in {group}."
    ),
    "totals_added": (
        "Counters: added {count} end-of-run total display line(s)."
    ),
    "skipped_no_group": (
        "Counters: no WORKING-STORAGE 01 group found; {count} counter "
        "reference(s) left undeclared."
    ),
    "skipped_no_anchor": (
        "Counters: no {anchor} statement found; end-of-run totals skipped."
    ),
}