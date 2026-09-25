# LOCATION: rules/db2_infrastructure_rules.py
# ACTION: ADD at the TOP of the file, directly under the module
#         docstring and `from __future__ import annotations`.
#         There must be NO later assignment to these four names.

# QUERYNO is owned by rules/cursor_declaration_rules.py.
# RE-EXPORT ONLY - see the QUERYNO note at the end of this file.
from rules.cursor_declaration_rules import (  # noqa: F401
    EMIT_QUERYNO,
    QUERYNO_BASE,
    QUERYNO_FIRST,
    QUERYNO_FIRST_ORDER,
    QUERYNO_STEP,
    QUERYNO_TEMPLATE,
)
# LOCATION: rules/db2_infrastructure_rules.py
# ACTION: REPLACE the entire appended block with this.
#         The import moves to the TOP of the file - see FILE 2.

# =====================================================================
# Area B indentation for generated DB2 blocks
# =====================================================================
# CHK-06.07 measures every generated DB2 block line and requires at
# least 4 body spaces, i.e. physical column 12. The manual reference
# places EXEC SQL, END-EXEC, EVALUATE SQLCODE and END-EVALUATE at
# column 12.
#
# InfrastructureBlockBuilder previously emitted "EXEC SQL" with no
# indent at all, so all 26 generated infrastructure lines landed in
# Area A and the check failed.
#
# Body indents are relative to column 8.
#
# NOTE - rules/cursor_declaration_rules.py declares IND_SELECT_FIRST and
# IND_SELECT_NEXT with DIFFERENT values. That is not an accident and not
# a duplicate: the two renderers emit different shapes.
#
#     this module              -> CursorDeclareBuilder   (LIVE)
#                                 SELECT on its own line, columns under it
#     cursor_declaration_rules -> CursorDeclarationGenerator (legacy)
#                                 "SELECT <column>" on one line
#
# When the legacy generator is deleted, delete its indents with it and
# these become the only copy. Until then, do NOT "unify" them - the
# output shapes genuinely differ.
ENFORCE_AREA_B_SQL_INDENT = True

IND_EXEC = "    "                # column 12 - EXEC SQL, END-EXEC
IND_SQL_BODY = "      "          # column 14 - DECLARE, SELECT, FROM
IND_SELECT_FIRST = "        "    # column 16 - first SELECT column
IND_SELECT_NEXT = "       "      # column 15 - comma aligns under the name
IND_WHERE_NEXT = "        "      # column 16 - conditions under WHERE
IND_88_LEVEL = "    "            # column 12 - 88 condition names

# =====================================================================
# SQL tokens
# =====================================================================
TOKEN_EXEC_SQL = "EXEC SQL"
TOKEN_END_EXEC = "END-EXEC."
TOKEN_SELECT = "SELECT"
TOKEN_WHERE = "WHERE"
TOKEN_ORDER_BY = "ORDER BY"
TOKEN_FOR_READ_ONLY = "FOR READ ONLY"

DECLARE_TEMPLATE = "DECLARE {cursor} CURSOR WITH HOLD FOR"
FROM_TEMPLATE = "FROM {table}"
SELECT_ITEM_FIRST_TEMPLATE = "{column}"
SELECT_ITEM_NEXT_TEMPLATE = ", {column}"
SELECT_ALL = "*"

# =====================================================================
# Cursor end-of-cursor flags
# =====================================================================
FLAG_NAME_TEMPLATE = "WS-{cursor}-FLAG"
NOT_EOC_TEMPLATE = "{cursor}-NOT-EOC"
EOC_TEMPLATE = "{cursor}-EOC"

FLAG_DECLARATION_TEMPLATE = "01  {name:<30} PIC X."
CONDITION_TEMPLATE = "88  {name:<26} VALUE '{value}'."

VALUE_NOT_EOC = "N"
VALUE_EOC = "Y"

# =====================================================================
# SQL-LOCATION
# =====================================================================
SQL_LOCATION_DECLARATION_TEMPLATE = "01  {name:<30} {picture}"

# =====================================================================
# Warnings emitted INTO the generated COBOL
# =====================================================================
MISSING_CURSOR_NAME = (
    "* DB2 WARNING: Unable to declare cursor; missing cursor name."
)
MISSING_TABLE_TEMPLATE = (
    "* DB2 WARNING: Unable to declare cursor {cursor}; "
    "missing DB2 table mapping."
)

# =====================================================================
# QUERYNO
# =====================================================================
# DELIBERATELY ABSENT.
#
# EMIT_QUERYNO, QUERYNO_BASE, QUERYNO_STEP and QUERYNO_TEMPLATE are
# RE-EXPORTED from rules/cursor_declaration_rules.py at the TOP of this
# file. They must never be assigned here.
#
# This module previously declared its own copies:
#
#     QUERYNO_BASE     = 254      vs  100  in the other module
#     QUERYNO_TEMPLATE = "{queryno}"  vs  "{number}"
#
# cursor_declare_builder.py imports its SQL tokens from HERE and QUERYNO
# from THERE, so the generated DECLARE carried QUERYNO 119 while the
# manual reference carries 254 - and swapping the template placeholder
# raises KeyError at render time, because the builder renders with
# .format(number=...).
#
# Re-exporting above and assigning below would shadow the import and
# restore the defect, so nothing is assigned here at all.