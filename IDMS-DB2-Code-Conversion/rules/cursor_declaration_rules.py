# LOCATION: rules/cursor_declaration_rules.py
# ACTION: CREATE NEW FILE
"""DB2 cursor DECLARE statement layout rules.

Layout follows the COBOL team's manual reference program:

    EXEC SQL DECLARE DZBEFFC1 CURSOR WITH HOLD FOR
      SELECT CO_IDPRKSK_479BEFF
           , NS_IRMOSTK_479BEFF
      FROM DZBEFFTV
      FOR READ ONLY
             QUERYNO 176
    END-EXEC

Constants only. No regex, no runtime logic, no program / record / table /
cursor / host variable names.
"""

from __future__ import annotations

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
IND_EXEC = "    "              # column 12
IND_CLAUSE = "      "          # column 14
IND_SELECT_FIRST = "      "    # column 14
IND_SELECT_NEXT = "           "  # column 19 - aligns comma under SELECT
IND_WHERE_NEXT = "        "    # column 16 - aligns AND under WHERE
IND_QUERYNO = "             "  # column 21

# ---------------------------------------------------------------------
# QUERYNO
# ---------------------------------------------------------------------
# DB2 EXPLAIN identifies a statement by QUERYNO. The manual programmer
# uses the source line number; the converter emits a stable derived
# value so repeated runs are byte-identical.
EMIT_QUERYNO = True
QUERYNO_TEMPLATE = "QUERYNO {number}"
QUERYNO_BASE = 100
QUERYNO_STEP = 19

# ---------------------------------------------------------------------
# Parent / child classification
# ---------------------------------------------------------------------
# A cursor with no WHERE clause is a parent/root cursor and must not
# carry ORDER BY. A cursor with a WHERE clause is a child cursor and
# keeps its ORDER BY.
PARENT_CURSOR_KEEPS_ORDER_BY = False
CHILD_CURSOR_KEEPS_ORDER_BY = True

# ---------------------------------------------------------------------
# WHERE column ownership
# ---------------------------------------------------------------------
# The left operand of a child join predicate must be a column of the
# cursor's own FROM table. Anything else produces SQLCODE -206 at bind.
ENFORCE_WHERE_COLUMN_OWNERSHIP = True
CHILD_JOIN_PREDICATE_TEMPLATE = "{child_column} = :{parent_group}.{parent_host}"
UNRESOLVED_JOIN_KEY_TEMPLATE = (
    "* DB2 WARNING: Unable to declare cursor {cursor}; join key "
    "{column} is not a column of {table}."
)

# ---------------------------------------------------------------------
# Termination
# ---------------------------------------------------------------------
# Every declaration except the last closes with a bare END-EXEC.
# The last one in the block closes the WORKING-STORAGE sentence with a
# period, matching the manual reference.
LAST_DECLARATION_TERMINATOR = "."

# ---------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------
DECLARATION_MESSAGES = {
    "declared_cursor": (
        "Cursor declaration: declared {cursor} on {table} "
        "with {count} column(s), QUERYNO {queryno}."
    ),
    "order_by_removed": (
        "Cursor declaration: removed ORDER BY from parent cursor {cursor}."
    ),
    "join_key_unresolved": (
        "Cursor declaration: join key {column} is not a column of {table}; "
        "cursor {cursor} was not declared."
    ),
}