# LOCATION: rules/cursor_order_cleanup_rules.py
# ACTION: CREATE NEW FILE
"""Cursor ORDER BY cleanup rules.

Constants only. No regex, no runtime logic, no program / record / table /
cursor / host variable names.

WHY THIS EXISTS

CursorOrderCleanupComposer was written to remove ORDER BY clauses the
CONVERTER had invented - CursorOrderByResolver derives them from Sheet
Mapping primary keys, which is a guess. The composer could not tell a
guessed clause from a resolved one, so it removed both.

Manual reference VMDZ7200 (Train Case 3) orders its root cursor on
NR_ID_479BFAS ASC. The clause carries business meaning and must survive.

The correct place to stop a guess is at the point of the guess, not by
deleting rendered SQL afterwards. This pass is therefore OFF.
"""

from __future__ import annotations

# Master switch. OFF: the composer is a no-op and reports why.
ENFORCE_PARENT_CURSOR_ORDER_BY_CLEANUP = False

CURSOR_ORDER_CLEANUP_MESSAGES = {
    "disabled": (
        "Cursor ORDER BY cleanup: pass disabled; ORDER BY is retained on "
        "every cursor (manual reference VMDZ7200 orders its root cursor)."
    ),
    "removed": (
        "Cursor ORDER BY cleanup: removed ORDER BY from {count} "
        "parent/root cursor declaration(s)."
    ),
    "none_found": (
        "Cursor ORDER BY cleanup: no parent/root cursor ORDER BY found."
    ),
}