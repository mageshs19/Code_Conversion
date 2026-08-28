"""
COBOL cleanup rule constants.

This file contains COBOL post-conversion cleanup constant values and message
text only. No regex patterns and no runtime logic belong here.
Rules belong in rules/, patterns in patterns/.
"""

# Generated Working-Storage declaration for the DB2 status flag.
SW_STATUS_D_DECLARATION = (
    "    10  SW-STATUS-D              PIC X    VALUE 'N'."
)

# Generated flag group line used when no WS-STATUS anchor exists.
# NOTE: This literal is emitted into the converted COBOL output, so its value
# is preserved exactly to avoid changing generated program behavior.
WS_DB2_FLAGS_GROUP = " 01  WS-DB2-FEEDBACK-FLAGS."

# Statement starters that stop the backward MOVE-block scan.
STOP_BACKWARD_SCAN_WORDS = (
    "IF ",
    "ELSE",
    "END-IF",
    "PERFORM ",
    "EVALUATE ",
    "WHEN ",
    "WRITE ",
    "EXEC SQL",
    "END-EXEC",
    "OPEN ",
    "CLOSE ",
    "READ ",
    "STOP ",
    "EXIT",
)

# Cursor paragraph number at/above which a fetch is treated as child/nested.
CHILD_FETCH_MINIMUM_NUMBER = 800

# Look-back / look-ahead window sizes.
MOVE_N_LOOKBACK_WINDOW = 3
OUTPUT_MOVE_SCAN_WINDOW = 60
INITIALIZE_LOOKBACK_WINDOW = 3

# LOCATION: rules/cobol_cleanup_rules.py
# ACTION: REPLACE the entire CLEANUP_MESSAGES = { ... } dictionary with this

CLEANUP_MESSAGES = {
    "added_dclgen_include": (
        "Cleanup: added missing DCLGEN include {table}."
    ),
    "replaced_error_status": (
        "Cleanup: replaced ERROR-STATUS move with SW-STATUS-D flag."
    ),
    "declared_sw_status_d_ws": (
        "Cleanup: declared SW-STATUS-D working-storage flag."
    ),
    "declared_sw_status_d_block": (
        "Cleanup: declared SW-STATUS-D in generated flag block."
    ),
    "child_fetch_early_stop": (
        "Cleanup: added SW-STATUS-D early-stop to child fetch loop."
    ),
    "moved_initialize": (
        "Cleanup: moved INITIALIZE before output population for {record}."
    ),
    "converted_db2_date_move": (
        "Cleanup: converted DB2 date move before output write."
    ),
    "removed_residual_idms_comment": (
        "Cleanup: removed residual IDMS conversion comment noise."
    ),
    "removed_orphan_continue": (
        "Cleanup: removed redundant CONTINUE after removed IDMS statement."
    ),
}

# LOCATION: rules/update_sql_cleanup_rules.py
# ACTION: APPEND these constants to the existing file (add at the end)

# --- Category E: manual-standard UPDATE block ---

# QUERYNO value appended to generated SQL statements (manual standard).
# The manual programmer uses the line/paragraph number; we emit a stable
# generated value so DB2 EXPLAIN can identify the statement.
UPDATE_QUERYNO = "442"

# When True, generated UPDATE uses EVALUATE SQLCODE (manual standard) instead
# of the older IF SQLCODE NOT = 0 form.
USE_EVALUATE_SQLCODE = True