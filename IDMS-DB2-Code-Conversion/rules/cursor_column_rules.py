from __future__ import annotations

"""
Rules for cursor SELECT and ORDER BY column resolution.

This module contains constants only.
No resolver logic, parser logic, or program-specific names belong here.
"""


CURSOR_COLUMN_SELECT_RULES = [
    "Prefer columns used by COBOL procedure field usage analysis.",
    "Include parent key columns required by child cursor relationships.",
    "Include child order key columns for child cursors.",
    "Exclude audit columns from cursor SELECT lists.",
    "Fallback to mapped DCLGEN-valid columns only when usage is unavailable.",
]


CURSOR_COLUMN_ORDER_RULES = [
    "Parent/root cursors do not receive ORDER BY unless mapping metadata indicates ordering.",
    "Child cursors may order by non-FK primary or sequence columns.",
    "DESC is applied only when metadata indicates sequence/event/latest-first semantics.",
]


ORDER_HINT_WORDS = (
    "ORDER",
    "ORDERBY",
    "SORT",
    "SORTKEY",
    "RANK",
)


DESC_HINT_WORDS = (
    "SEQ",
    "SEQUENCE",
    "IDMSKEY",
    "IDENTIFIERSEQ",
    "IDENTIFIERSEQSPECIAL",
    "EVENT",
    "EVPR",
    "EVEF",
    "AUTO",
    "INCREMENT",
)