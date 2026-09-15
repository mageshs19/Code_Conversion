# LOCATION: rules/sql_error_rules.py
# ACTION: CREATE NEW FILE
"""SQLERROR routine constants.

Constants only. No regex, no runtime logic, no program / record / table /
cursor / host variable names.
"""

from __future__ import annotations

SQL_ERROR_PARAGRAPH_NAME = "SQLERROR"
LEGACY_SQL_ERROR_PARAGRAPH_NAME = "SQL-ERROR"
SQL_ERROR_INCLUDE_NAME = "SQLERROR"

# --- Paragraph header policy -----------------------------------------
# Decision D-1 CLOSED by the COBOL team's manual reference program.
# The SQLERROR copybook supplies the paragraph label; emitting a local
# header duplicates it and the compiler rejects the program.
EMIT_SQL_ERROR_PARAGRAPH_HEADER = False

SQL_ERROR_BANNER = "* SQLERROR ROUTINE."

# --- Body indents, relative to column 8 ------------------------------
IND_STATEMENT = "    "       # column 12
IND_SQL_BODY = "         "   # column 17

# --- Old-body recognition --------------------------------------------
# Tokens that identify a previously generated SQLERROR body so it can be
# consumed and replaced. Covers both known historical forms:
#   (a) EXEC SQL / INCLUDE SQLERROR / END-EXEC
#   (b) DISPLAY 'SQL ERROR AT : ' / DISPLAY 'SQLCODE : ' / CALL USERABEN
OLD_BLOCK_BODY_TOKENS = (
    "EXEC SQL",
    "INCLUDE SQLERROR",
    "END-EXEC",
    "SQL ERROR AT",
    "SQLCODE",
    "SQL-LOCATION",
    "CALL USERABEN",
    "CONTINUE",
)

# --- Diagnostics ------------------------------------------------------
SQL_ERROR_MESSAGES = {
    "routine_added": "SQLERROR: added generated SQLERROR routine.",
    "routine_replaced": "SQLERROR: replaced existing SQLERROR body with the include form.",
    "already_present": "SQLERROR: routine already present; not duplicated.",
    "renamed_legacy": (
        "SQLERROR: renamed {headers} legacy header(s) and {performs} "
        "legacy PERFORM(s) from SQL-ERROR to SQLERROR."
    ),
}