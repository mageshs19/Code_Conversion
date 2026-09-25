# LOCATION: rules/cursor_declaration_rules.py
# ACTION: REPLACE ENTIRE FILE
"""DB2 cursor DECLARE statement layout rules.

Layout follows the COBOL team's manual reference program:

    EXEC SQL DECLARE DZBFASC1 CURSOR WITH HOLD FOR
      SELECT CT_RKTGDSV_479BFAS
           , NR_ID_479BFAS
      FROM DZBFASTV
      ORDER BY NR_ID_479BFAS ASC
      FOR READ ONLY
             QUERYNO 254
    END-EXEC

Constants only. No regex, no runtime logic, no program / record / table /
cursor / host variable names.

CORRECTION 1 - the same constant was assigned twice in this file
------------------------------------------------------------------
EMIT_QUERYNO, QUERYNO_BASE, QUERYNO_STEP, QUERYNO_TEMPLATE,
PARENT_CURSOR_KEEPS_ORDER_BY and CHILD_CURSOR_KEEPS_ORDER_BY each
appeared TWICE, 180+ lines apart, with different values. Python keeps
the LAST assignment, so the effective value depended on line order and
nothing in the code said so.

Every name is now assigned exactly once. tests/test_rules_no_duplicate
_constants.py fails the build if that is ever undone.

CORRECTION 2 - QUERYNO did not match the manual reference
-----------------------------------------------------------
The generated DECLARE carried

    QUERYNO 119   =  100 + (1 x 19)

while the manual reference VMDZ7200 carries QUERYNO 254. DB2 EXPLAIN
identifies a statement by QUERYNO; a number the reference does not use
cannot be tied back to the documented access path.

CURSOR ORDER IS 1-BASED - CURSOR_PARAGRAPH_NUMBERING is keyed 1/2/3 and
the first cursor renders 710/720/730. The renderer computes

    QUERYNO_BASE + (cursor_order x QUERYNO_STEP)

so QUERYNO_BASE is NOT the first value; it is the value at order 0. It
is therefore DERIVED from the reference value below, which keeps the
renderer and the existing tests unchanged.

CORRECTION 3 - the template placeholder must stay {number}
-------------------------------------------------------------
cursor_declare_builder.py renders with

    QUERYNO_TEMPLATE.format(number=...)

rules/db2_infrastructure_rules.py used "{queryno}". Swapping the two
raises KeyError at render time. {number} is the live contract and is
kept; db2_infrastructure_rules re-exports from here and assigns nothing.

CORRECTION 4 - a counter rule was pasted into this module
------------------------------------------------------------
TOTALS_ANCHOR_STATEMENTS belongs to rules/counter_declaration_rules.py
and has been removed from here. It is unrelated to cursor declarations.

CORRECTION 5 - ORDER_BY_KEY_MESSAGES was assigned twice
---------------------------------------------------------
The identity-key narrowing constants were appended to the end of this
file while an earlier copy of ORDER_BY_KEY_MESSAGES already existed
further up. Two dictionary literals, different wording, different
placeholders: the first copy's "narrowed_to_identity" had no {kept}
field, the second did, and only line order decided which one a build
used. That is CORRECTION 1 happening a second time in the same module.

There is now ONE ORDER_BY_KEY_MESSAGES literal, and every ORDER BY
behaviour switch and provenance label lives in the ORDER BY section
where it can be read in one place.

KEY-SPACE CONTRACT
------------------
CursorOrderByResolver merges ORDER_BY_KEY_MESSAGES with
CURSOR_ORDER_BY_MESSAGES into one catalogue. The two key sets MUST stay
DISJOINT - a collision would silently shadow a diagnostic.
tests/test_rules_no_duplicate_constants.py asserts that too.
"""

from __future__ import annotations

# NON_COLUMN_SENTINELS is owned by the record materialisation rules.
# Re-exported, never re-declared: a second copy diverges the day one of
# them gains a new sentinel. It is listed in __all__ so an import
# cleanup cannot remove what cursor_declare_builder.py imports from here.
from rules.record_materialisation_rules import (  # noqa: F401
    NON_COLUMN_SENTINELS,
)

# ---------------------------------------------------------------------
# Statement form
# ---------------------------------------------------------------------
# True  -> EXEC SQL DECLARE <cursor> CURSOR WITH HOLD FOR   (manual)
# False -> EXEC SQL / DECLARE <cursor> CURSOR WITH HOLD FOR (two lines)
DECLARE_ON_EXEC_SQL_LINE = True

DECLARE_LINE_TEMPLATE = "EXEC SQL DECLARE {cursor} CURSOR WITH HOLD FOR"
SELECT_FIRST_TEMPLATE = "SELECT {column}"
SELECT_NEXT_TEMPLATE = ", {column}"
FROM_TEMPLATE = "FROM {table}"
WHERE_FIRST_TEMPLATE = "WHERE {condition}"
WHERE_NEXT_TEMPLATE = "AND {condition}"
ORDER_BY_TEMPLATE = "ORDER BY {columns}"
FOR_READ_ONLY = "FOR READ ONLY"
END_EXEC = "END-EXEC"

# ---------------------------------------------------------------------
# Body indents, relative to column 8
# ---------------------------------------------------------------------
IND_EXEC = "    "                # column 12
IND_CLAUSE = "      "            # column 14
IND_SELECT_FIRST = "      "      # column 14
IND_SELECT_NEXT = "           "  # column 19 - comma under SELECT
IND_WHERE_NEXT = "        "      # column 16 - AND under WHERE
IND_QUERYNO = "             "    # column 21

# ---------------------------------------------------------------------
# QUERYNO
# ---------------------------------------------------------------------
# SINGLE SOURCE OF TRUTH. rules/db2_infrastructure_rules.py re-exports
# these names and must never redefine them.
EMIT_QUERYNO = True

# Placeholder name is part of the render contract. See CORRECTION 3.
QUERYNO_TEMPLATE = "QUERYNO {number}"

# The manual reference value for the FIRST cursor in a program.
QUERYNO_FIRST = 254

# Cursor order is 1-based, and the renderer computes
# QUERYNO_BASE + (order x QUERYNO_STEP). QUERYNO_BASE is therefore the
# value at order 0 and is DERIVED, so changing QUERYNO_FIRST alone moves
# every generated number and nothing else has to be touched.
QUERYNO_STEP = 1
QUERYNO_FIRST_ORDER = 1
QUERYNO_BASE = QUERYNO_FIRST - (QUERYNO_FIRST_ORDER * QUERYNO_STEP)

# ---------------------------------------------------------------------
# ORDER BY - retention
# ---------------------------------------------------------------------
# EVIDENCE TRAIL - a rule constant with no cited reference program is an
# assumption, not a site standard.
#
#   OBSERVED IN  : the BEFF / EVEF manual reference family, whose driving
#                  cursor carries no ORDER BY. That is where
#                  "the manual reference never orders a parent cursor"
#                  came from, and why this was once False.
#
#   CONTRADICTED : manual reference VMDZ7200 (Train Case 3) ends its ROOT
#                  cursor with ORDER BY NR_ID_479BFAS ASC.
#
#   DECISION     : retain ORDER BY on every cursor. Row sequence is
#                  business meaning - the output extract inherits it - so
#                  deleting the clause silently reorders the file for
#                  every downstream consumer.
#
#   RULE         : the converter may REFUSE to generate a clause it
#                  cannot resolve. It must never DELETE one that has been
#                  resolved.
PARENT_CURSOR_KEEPS_ORDER_BY = True
CHILD_CURSOR_KEEPS_ORDER_BY = True

# Master switch. Set False ONLY to reproduce the pre-correction output
# for a side-by-side diff; it is not a site standard.
ENFORCE_ORDER_BY_RETENTION = True

# ---------------------------------------------------------------------
# ORDER BY - column ownership
# ---------------------------------------------------------------------
# ORDER BY is resolved upstream as free text, so an entry may carry a
# sort direction: "NR_ID_479BFAS ASC".
#
# The COLUMN part must be a real column of the cursor's own FROM table.
# A generated declaration once carried
#
#     , FILLER
#
# which is a COBOL placeholder, not a DB2 column, and binds as
# SQLCODE -206 - the whole program fails to run.
ENFORCE_ORDER_BY_COLUMN_OWNERSHIP = True

ORDER_BY_DIRECTIONS = ("ASC", "DESC")

# ---------------------------------------------------------------------
# ORDER BY - key width
# ---------------------------------------------------------------------
#   OBSERVED IN  : manual reference VMDZ7200 (Train Case 3) ends its ROOT
#                  cursor with ORDER BY NR_ID_479BFAS ASC - the single
#                  identity key, ascending.
#
#   RECORD       : that record's CALC key is 8 columns wide and includes
#                  a FILLER placeholder that is not a DB2 column at all.
#
#   BASIS        : the identity column is an auto-increment surrogate key
#                  ("auto increment seq key" in the Sheet Mapping),
#                  unique on its own, so the remaining composite columns
#                  cost sort effort and add no determinism.
#
#   RULE         : narrow to the identity key WHEN ONE EXISTS. A record
#                  with NO identity key keeps its full composite key - a
#                  resolved clause is refused, never deleted.
#
#   CONSISTENCY  : this is the SAME narrowing the UPDATE WHERE clause
#                  applies (key_column_mixin), reading the SAME prefix
#                  list from rules/key_naming_rules.py. One key
#                  definition, two clauses.
ORDER_BY_PREFER_IDENTITY_KEY = True

# A child cursor is already qualified by the parent key in WHERE, so the
# identity key alone is still a total order inside the result set. Set
# False only for a record whose sequence-within-parent is business
# meaning and is NOT expressed by the identity key.
ORDER_BY_NARROWING_APPLIES_TO_CHILD = True

# ---------------------------------------------------------------------
# ORDER BY - provenance labels
# ---------------------------------------------------------------------
# ONE place. These feed the {source} field of CURSOR_ORDER_BY_MESSAGES
# ["resolved"], so every producer of that message must pass one of them.
ORDER_BY_SOURCE_PRIMARY_KEY = "Sheet Mapping primary key"
ORDER_BY_SOURCE_PARENT_INTENT = "Sheet Mapping order semantics"
ORDER_BY_SOURCE_CHILD_KEY = "relationship key"

# ---------------------------------------------------------------------
# WHERE qualification
# ---------------------------------------------------------------------
# The left operand of a child join predicate must be a column of the
# cursor's own FROM table. Anything else produces SQLCODE -206 at bind.
ENFORCE_WHERE_COLUMN_OWNERSHIP = True

CHILD_JOIN_PREDICATE_TEMPLATE = "{child_column} = :{parent_group}.{parent_host}"

# A cursor with no WHERE is a root/sweep cursor. That is CORRECT for an
# IDMS area sweep (FIND EACH <rec> WITHIN <area>) and WRONG for a
# qualified access whose Sheet Mapping rows were never classified as
# FOREIGN.
#
# The fallback qualifies the CHILD column against a PARENT host. It never
# compares a column to its own group: "COL = :OWNGROUP.COL" is a
# meaningless filter, not a join.
EMIT_DRIVING_KEY_PREDICATE = True

DRIVING_KEY_PREDICATE_TEMPLATE = "{child_column} = :{parent_group}.{parent_host}"

# ---------------------------------------------------------------------
# Warnings emitted INTO the generated COBOL
# ---------------------------------------------------------------------
UNRESOLVED_JOIN_KEY_TEMPLATE = (
    "* DB2 WARNING: Unable to declare cursor {cursor}; join key "
    "{column} is not a column of {table}."
)
MISSING_COLUMNS_TEMPLATE = (
    "* DB2 WARNING: Unable to declare cursor {cursor}; no mapped DCLGEN "
    "column was resolved for {table}."
)

# ---------------------------------------------------------------------
# Termination
# ---------------------------------------------------------------------
# Every declaration except the last closes with a bare END-EXEC.
# The last one in the block closes the WORKING-STORAGE sentence with a
# period, matching the manual reference.
LAST_DECLARATION_TERMINATOR = "."

# ---------------------------------------------------------------------
# Declaration diagnostics
# ---------------------------------------------------------------------
# ONE dictionary literal. Post-hoc "DECLARATION_MESSAGES[key] = ..."
# assignments are what let the duplicate QUERYNO block hide in this file.
DECLARATION_MESSAGES = {
    "declared_cursor": (
        "Cursor declaration: declared {cursor} on {table} "
        "with {count} column(s), QUERYNO {queryno}."
    ),
    "where_declared": (
        "Cursor declaration: {cursor} qualified by {count} predicate(s)."
    ),
    "join_key_unresolved": (
        "Cursor declaration: join key {column} is not a column of {table}; "
        "cursor {cursor} was not declared."
    ),
    "select_all_refused": (
        "Cursor declaration: {cursor} has no explicit column list; "
        "SELECT * refused."
    ),
    "order_by_kept": (
        "Cursor declaration: {cursor} keeps ORDER BY on {count} column(s)."
    ),
    "order_by_none": (
        "Cursor declaration: {cursor} has no resolvable ORDER BY; row "
        "sequence is whatever DB2 chooses. Confirm the extract does not "
        "depend on order."
    ),
    "order_by_column_dropped": (
        "Cursor declaration: dropped ORDER BY entry '{entry}' from "
        "{cursor}; {column} is not a column of {table}."
    ),
    "order_by_all_dropped": (
        "Cursor declaration: every ORDER BY entry for {cursor} was "
        "rejected; the clause is omitted and rows return in DB2 sequence."
    ),
    # Retained for the legacy path, reachable only when
    # ENFORCE_ORDER_BY_RETENTION is switched off for a diff.
    "order_by_removed": (
        "Cursor declaration: removed ORDER BY from parent cursor {cursor}."
    ),
}

# ---------------------------------------------------------------------
# Sweep reporting
# ---------------------------------------------------------------------
SWEEP_CURSOR_NO_WHERE_TEMPLATE = (
    "Cursor declaration: {cursor} on {table} declared WITHOUT a WHERE "
    "clause (root/sweep access). Confirm this is a full-table read."
)

# ---------------------------------------------------------------------
# Join resolver diagnostics
# ---------------------------------------------------------------------
JOIN_MESSAGES = {
    "no_resolution": (
        "Cursor join: no relationship resolution for {record}; "
        "attempting driving-key qualification."
    ),
    "no_fk_rows": (
        "Cursor join: {record} has no foreign-key row in the Sheet "
        "Mapping; attempting driving-key qualification."
    ),
    "unowned_column": (
        "Cursor join: {column} is not a column of {table}; "
        "predicate skipped."
    ),
    "no_parent_host": (
        "Cursor join: no DCLGEN host variable for parent column "
        "{column}; predicate skipped."
    ),
    "no_parent_side": (
        "Cursor join: {record} has no resolvable parent table and no "
        "driving host was supplied; WHERE not generated."
    ),
    "no_child_table": (
        "Cursor join: no DB2 table for {record}; WHERE not generated."
    ),
    "sweep": (
        "Cursor join: {record} resolves to an unqualified root/sweep "
        "read; no WHERE generated."
    ),
}

# ---------------------------------------------------------------------
# ORDER BY resolver diagnostics - column selection
# ---------------------------------------------------------------------
# ONE dictionary serving BOTH producers - RelationshipKeyColumnResolver
# and CursorOrderByResolver. rules/cursor_column_rules.py re-exports it
# rather than declaring a second copy.
#
# "resolved" carries {source}: every caller must pass one of the
# ORDER_BY_SOURCE_* labels above.
CURSOR_ORDER_BY_MESSAGES = {
    "resolved": (
        "Cursor ORDER BY: {record} resolved {count} column(s) from the "
        "{source}: {columns}."
    ),
    "empty_no_primary_key": (
        "Cursor ORDER BY: {record} has no primary-key column in the "
        "Sheet Mapping, so no ORDER BY can be inferred. The cursor will "
        "return rows in whatever sequence DB2 chooses. Flag the key "
        "column in the Sheet Mapping, or supply the IDMS schema so the "
        "set sort key can be used."
    ),
    "empty_all_foreign": (
        "Cursor ORDER BY: every primary-key column of {record} is also "
        "a foreign key, so none survived; no ORDER BY inferred."
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

# ---------------------------------------------------------------------
# ORDER BY resolver diagnostics - key width
# ---------------------------------------------------------------------
# ONE literal. See CORRECTION 5. Keys MUST NOT collide with
# CURSOR_ORDER_BY_MESSAGES: the resolver merges both catalogues.
ORDER_BY_KEY_MESSAGES = {
    "single_key": (
        "Cursor ORDER BY: {record} already orders on a single column: "
        "{columns}."
    ),
    "narrowed_to_identity": (
        "Cursor ORDER BY: {record} has a {total}-part composite key; "
        "narrowed to {kept} identity key column(s): {columns}. A "
        "surrogate key is unique on its own, so the wider key adds sort "
        "cost without adding determinism; row sequence is unchanged."
    ),
    "kept_composite": (
        "Cursor ORDER BY: {record} has no identity-style key column; "
        "ordering by the full {total}-part composite key so the cursor "
        "remains deterministic."
    ),
    "kept_composite_child": (
        "Cursor ORDER BY: {record} is a child cursor and identity "
        "narrowing is disabled for children; {total} column(s) retained."
    ),
}

# ---------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------
# Explicit, so the NON_COLUMN_SENTINELS re-export cannot be removed by an
# import cleanup - cursor_declare_builder.py imports it from HERE.
__all__ = [
    # re-export
    "NON_COLUMN_SENTINELS",
    # statement form
    "DECLARE_ON_EXEC_SQL_LINE",
    "DECLARE_LINE_TEMPLATE",
    "SELECT_FIRST_TEMPLATE",
    "SELECT_NEXT_TEMPLATE",
    "FROM_TEMPLATE",
    "WHERE_FIRST_TEMPLATE",
    "WHERE_NEXT_TEMPLATE",
    "ORDER_BY_TEMPLATE",
    "FOR_READ_ONLY",
    "END_EXEC",
    # indents
    "IND_EXEC",
    "IND_CLAUSE",
    "IND_SELECT_FIRST",
    "IND_SELECT_NEXT",
    "IND_WHERE_NEXT",
    "IND_QUERYNO",
    # queryno
    "EMIT_QUERYNO",
    "QUERYNO_TEMPLATE",
    "QUERYNO_FIRST",
    "QUERYNO_FIRST_ORDER",
    "QUERYNO_STEP",
    "QUERYNO_BASE",
    # order by
    "PARENT_CURSOR_KEEPS_ORDER_BY",
    "CHILD_CURSOR_KEEPS_ORDER_BY",
    "ENFORCE_ORDER_BY_RETENTION",
    "ENFORCE_ORDER_BY_COLUMN_OWNERSHIP",
    "ORDER_BY_DIRECTIONS",
    "ORDER_BY_PREFER_IDENTITY_KEY",
    "ORDER_BY_NARROWING_APPLIES_TO_CHILD",
    "ORDER_BY_SOURCE_PRIMARY_KEY",
    "ORDER_BY_SOURCE_PARENT_INTENT",
    "ORDER_BY_SOURCE_CHILD_KEY",
    # where
    "ENFORCE_WHERE_COLUMN_OWNERSHIP",
    "CHILD_JOIN_PREDICATE_TEMPLATE",
    "EMIT_DRIVING_KEY_PREDICATE",
    "DRIVING_KEY_PREDICATE_TEMPLATE",
    # warnings / termination
    "UNRESOLVED_JOIN_KEY_TEMPLATE",
    "MISSING_COLUMNS_TEMPLATE",
    "SWEEP_CURSOR_NO_WHERE_TEMPLATE",
    "LAST_DECLARATION_TERMINATOR",
    # diagnostics
    "DECLARATION_MESSAGES",
    "JOIN_MESSAGES",
    "CURSOR_ORDER_BY_MESSAGES",
    "ORDER_BY_KEY_MESSAGES",
]