# LOCATION: rules/db2_infrastructure_rules.py
# ACTION: APPEND at the end of the file

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
# Warnings
# =====================================================================
MISSING_CURSOR_NAME = (
    "* DB2 WARNING: Unable to declare cursor; missing cursor name."
)
MISSING_TABLE_TEMPLATE = (
    "* DB2 WARNING: Unable to declare cursor {cursor}; "
    "missing DB2 table mapping."
)