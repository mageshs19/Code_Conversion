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

ENFORCE_ORDER_BY_COLUMN_VALIDATION = True

# Tokens that are never a DB2 column, whatever the Sheet Mapping says.
NON_COLUMN_SENTINELS = ("", "FILLER", "N/A", "NA", "-", "NONE")

#
# --- ORDER BY direction ----------------------------------------------
#
# CORRECTION - a sort direction was inferred by SUBSTRING match over free
# text. The haystack included remarks, basetype, the DB2 data type AND
# the column name, so
#
#     "DESC" in "DESCRIPTION"   ->  True
#
# Any row whose Remarks mentioned a description silently reversed that
# column's sort order. Row sequence in the extract file is business
# meaning; it must never be decided by prose.
#
# Direction inference is now OFF. The manual reference emits a plain
# ASC. Turn this on only with a DEDICATED Sheet Mapping column that
# states the direction explicitly - never a remarks field.
EMIT_ORDER_BY_DIRECTION = False

ORDER_BY_DIRECTION_ASC = "ASC"
ORDER_BY_DIRECTION_DESC = "DESC"

# Emitted after every column so the intent is explicit in the SQL,
# matching the manual reference: ORDER BY NR_ID_479BFAS ASC
EMIT_EXPLICIT_ASC = True

# Fields scanned for a direction hint when EMIT_ORDER_BY_DIRECTION is on.
# Deliberately EXCLUDES remarks, basetype, data type and the column name.
DESC_HINT_FIELDS = ("db2_key",)

CURSOR_ORDER_BY_MESSAGES = {
    "resolved": (
        "Cursor ORDER BY: {record} resolved {count} column(s): {columns}."
    ),
    "dropped_not_a_column": (
        "Cursor ORDER BY: dropped '{column}' for {record}; it is not a "
        "DB2 column of that record."
    ),
    "dropped_audit": (
        "Cursor ORDER BY: dropped audit column '{column}' for {record}."
    ),
    "dropped_sentinel": (
        "Cursor ORDER BY: dropped '{column}' for {record}; it is a COBOL "
        "placeholder, not a DB2 column."
    ),
    "none": (
        "Cursor ORDER BY: {record} yielded no orderable column; the "
        "cursor returns rows in whatever sequence DB2 chooses."
    ),
    "direction_disabled": (
        "Cursor ORDER BY: direction inference is OFF; {count} column(s) "
        "default to {direction}."
    ),
}