from __future__ import annotations

# Update business SQL standardizer constants.
# Constants only. No regex, no runtime logic, no program/record/table names.

# --- Fixed-format column geometry ---
FIXED_BODY_WIDTH = 65
SEQUENCE_AREA_WIDTH = 6      # columns 1-6 (left sequence)
INDICATOR_COLUMN = 7        # column 7 (indicator area)
BODY_START_COLUMN = 7       # body begins after indicator (0-based slice at 7)
BODY_END_COLUMN = 72        # columns 8-72 are the body
FULL_LINE_WIDTH = 72        # a full fixed-format line reaches at least col 72
TOTAL_LINE_WIDTH = 80       # columns 73-80 are the right sequence
RIGHT_SEQUENCE_WIDTH = 8

# --- Generated indentation ---
AREA_B_INDENT = "    "        # 4 spaces -> physical column 12
SQL_BODY_INDENT = "       "   # 7 spaces -> nested SQL body
NESTED_INDENT = "        "    # 8 spaces -> nested EVALUATE/IF body
WHEN_INDENT = "    "          # WHEN clause indent inside EVALUATE

# --- Comment / indicator characters ---
COMMENT_INDICATORS = ("*", "/")
ACTIVE_INDICATOR = " "

# --- COBOL keyword tokens used for line classification ---
TOKEN_IF = "IF "
TOKEN_PERFORM = "PERFORM "
TOKEN_WHEN = "WHEN "
TOKEN_END_IF = "END-IF"
TOKEN_INITIALIZE_DCL = "INITIALIZE DCL"
TOKEN_INITIALIZE = "INITIALIZE"
TOKEN_EXEC_SQL = "EXEC SQL"
TOKEN_END_EXEC = "END-EXEC"
TOKEN_EVALUATE_SQLCODE = "EVALUATE SQLCODE"
TOKEN_END_EVALUATE = "END-EVALUATE"
TOKEN_STAR = "*"

# --- Fixed process/error paragraph names (COBOL-shop standard) ---
READ_FLAT_FILE_PARAGRAPH = "READ-FLAT-FILE"
SQL_ERROR_PARAGRAPH_NAMES = ("SQLERROR", "SQL-ERROR")
SQL_ERROR_ROUTINE_MARKER = "SQLERROR ROUTINE"

# --- Generated body templates ---
PERFORM_TEMPLATE = "PERFORM {paragraph}."
COMMIT_CHECK_IF_TEMPLATE = "IF {counter} > {threshold}"
COMMIT_CHECK_PERFORM_TEMPLATE = "{indent}PERFORM {commit_paragraph}"
END_IF_STATEMENT = "END-IF."
ADD_UPDATE_COUNTER_TEMPLATE = "ADD 1 TO {counter}"
INITIALIZE_DCL_GROUP_TEMPLATE = "INITIALIZE {group}."
FINAL_PERIOD_LINE = "    ."
LONE_PERIOD = "."

# --- Diagnostics (skip messages not already in UPDATE_RESTART_DIAGNOSTICS) ---
DIAG_PROCESS_PARAGRAPH_UNRESOLVED = (
    "Business update SQL standardization skipped. Processing paragraph "
    "could not be resolved."
)
DIAG_PROCESS_PARAGRAPH_NOT_FOUND_TEMPLATE = (
    "Business update SQL standardization skipped. Processing paragraph not "
    "found: {paragraph}."
)