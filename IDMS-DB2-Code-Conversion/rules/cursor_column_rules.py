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

ENFORCE_FULL_RECORD_SELECT = True

CURSOR_COLUMN_SELECT_RULES.append(
    "When a record is materialised from its DCLGEN group, the cursor "
    "SELECT covers every mapped DCLGEN column of that record."
)

CURSOR_COLUMN_MESSAGES = {
    "usage_only": (
        "Cursor columns: {record} resolved {count} column(s) from field "
        "usage analysis."
    ),
    "full_record_applied": (
        "Cursor columns: {record} extended from {usage} usage-driven "
        "column(s) to {total} mapped DCLGEN column(s) so every "
        "materialised field is fetched."
    ),
    "full_record_unavailable": (
        "Cursor columns: {record} has no resolvable full DCLGEN column "
        "set; kept the {count} usage-driven column(s)."
    ),
}
CURSOR_COLUMN_MESSAGES["usage_selector_missing"] = (
    "Cursor columns: {record} has no field-usage selector; the SELECT "
    "list is full-record only and column order is not usage-driven."
)
CURSOR_COLUMN_MESSAGES["usage_selector_failed"] = (
    "Cursor columns: {record} field-usage selection failed ({reason}); "
    "the SELECT list is full-record only."
)
CURSOR_COLUMN_MESSAGES["usage_selector_missing"] = (
    "Cursor columns: {record} has no field-usage selector; the SELECT "
    "list is full-record only and column order is not usage-driven."
)
CURSOR_COLUMN_MESSAGES["usage_selector_failed"] = (
    "Cursor columns: {record} field-usage selection failed ({reason}); "
    "the SELECT list is full-record only."
)