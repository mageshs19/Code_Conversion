from __future__ import annotations

"""
Rules for update COBOL final cleanup.

This module contains constants only.
No regex patterns, parser logic, service logic, program names, DB2 table names,
DCLGEN names, or host variable names belong here.
"""


UPDATE_FINAL_CLEANUP_RULES = [
    "Apply only generic final cleanup after COBOL conversion.",
    "Do not change business logic.",
    "Do not hardcode program names, DB2 tables, DB2 columns, DCLGEN groups, or host variables.",
    "Do not rewrite SQL DCLGEN dot references.",
    "Only rewrite non-SQL DCLGROUP.HOST references to COBOL OF format.",
    "Only initialize nearby resolved DCLGEN groups when local context is clear.",
    "Only insert audit moves for audit columns already present in generated UPDATE SET assignments.",
    "Only rewrite diagnostic labels when a nearby SQL table can be resolved.",
]


UPDATE_FINAL_LOOKAHEAD_LIMIT = 25
UPDATE_FINAL_LOOKBACK_DUPLICATE_LIMIT = 80


PROTECTED_BARE_TARGET_PREFIXES = (
    "WS-",
    "SW-",
    "WK-",
    "W-",
    "UIT-",
    "OUT-",
    "ES-",
    "SQL",
    "DCL",
    "ERROR-",
    "USER",
    "CS-",
    "TS-",
    "HR-",
    "HELP-",
    "PROGRAM-",
    "DA-",
    "DT-",
)


TIMESTAMP_AUDIT_PREFIXES = (
    "TS_UPDATE",
)


USER_AUDIT_PREFIXES = (
    "ID_USERID",
    "NR_USERID",
    "ID_USER",
    "NR_USER",
)


AUDIT_SOURCE_BY_KIND = {
    "timestamp": "TS-TIMESTAMP",
    "user": "CS-PROGRAM",
}

# --- Update final cleanup fixed-format geometry & tokens (appended) ---

# Fixed-format column geometry.
FINAL_CLEANUP_BODY_WIDTH = 65
FINAL_CLEANUP_SEQUENCE_WIDTH = 6     # columns 1-6
FINAL_CLEANUP_INDICATOR_COLUMN = 7   # column 7
FINAL_CLEANUP_BODY_START = 7
FINAL_CLEANUP_BODY_END = 72
FINAL_CLEANUP_FULL_WIDTH = 72
FINAL_CLEANUP_TOTAL_WIDTH = 80
FINAL_CLEANUP_RIGHT_SEQUENCE_WIDTH = 8

# Generated indentation.
FINAL_CLEANUP_AREA_B = "    "          # 4 spaces  -> column 12
FINAL_CLEANUP_SQL_BODY = "       "     # 7 spaces  -> nested SQL body
FINAL_CLEANUP_WHEN_INDENT = "        " # 8 spaces
FINAL_CLEANUP_ACTION_INDENT = "          "  # 10 spaces

# Comment / debug indicator characters.
FINAL_CLEANUP_COMMENT_INDICATORS = ("*", "/", "D", "d")
FINAL_CLEANUP_COMMENT_CHARS = ("*", "/")
FINAL_CLEANUP_DEBUG_PREFIX = "D "

# COBOL keyword tokens.
FINAL_CLEANUP_TOKEN_MOVE = "MOVE "
FINAL_CLEANUP_TOKEN_TO = " TO "
FINAL_CLEANUP_TOKEN_EXEC_SQL = "EXEC SQL"
FINAL_CLEANUP_TOKEN_END_EXEC = "END-EXEC"
FINAL_CLEANUP_TOKEN_EVALUATE_SQLCODE = "EVALUATE SQLCODE"
FINAL_CLEANUP_TOKEN_END_EVALUATE = "END-EVALUATE"
FINAL_CLEANUP_TOKEN_END_IF = "END-IF"
FINAL_CLEANUP_TOKEN_STOP_RUN = "STOP RUN."
FINAL_CLEANUP_TOKEN_END_IF_DOT = "END-IF."
FINAL_CLEANUP_TOKEN_PROCEDURE_DIVISION = "PROCEDURE DIVISION"
FINAL_CLEANUP_DCL_PREFIX = "DCL"
FINAL_CLEANUP_LONE_PERIOD = "."
FINAL_CLEANUP_DOT = "."

# Rewrite templates.
FINAL_CLEANUP_MOVE_TEMPLATE = "MOVE {source}"
FINAL_CLEANUP_FIELD_OF_GROUP_TEMPLATE = "{field} OF {group}"
FINAL_CLEANUP_TO_FIELD_OF_GROUP_TEMPLATE = "TO {field} OF {group}"

# Blank-line collapsing.
FINAL_CLEANUP_MAX_CONSECUTIVE_BLANKS = 2