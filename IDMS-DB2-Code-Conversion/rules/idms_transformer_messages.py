from __future__ import annotations

# IDMS statement transformer message/generated-line templates.
# All *DB2: text lives here so wording stays centralized.
# No regex, no logic, no hardcoded program/record/table names.

# ---- Removed control / declarative ----
REMOVED_CONTROL_STATEMENT_TEMPLATE = (
    "*DB2: Removed residual IDMS control statement: {line}"
)
REMOVED_BIND_TEMPLATE = "*DB2: Removed IDMS BIND statement: {line}"
REMOVED_USAGE_READY_TEMPLATE = "*DB2: Removed IDMS usage/READY statement: {line}"
REMOVED_CONNECT_TEMPLATE = "*DB2: Removed IDMS CONNECT statement: {line}"
REMOVED_DISCONNECT_TEMPLATE = "*DB2: Removed IDMS DISCONNECT statement: {line}"
REMOVED_STATUS_ABORT_TEMPLATE = (
    "*DB2: Removed IDMS status/abort paragraph call: {line}"
)
REMOVED_FIND_CURRENT_TEMPLATE = (
    "*DB2: Removed IDMS FIND CURRENT statement: {line}"
)

# ---- FINISH / COMMIT ----
FINISH_OUTSIDE_PROCEDURE_TEMPLATE = (
    "*DB2: FINISH ignored outside PROCEDURE DIVISION: {line}"
)
FINISH_CONVERTED_TO_COMMIT = "*DB2: IDMS FINISH converted to COMMIT."
COMMIT_OUTSIDE_PROCEDURE_TEMPLATE = (
    "*DB2: COMMIT ignored outside PROCEDURE DIVISION: {line}"
)

# ---- OBTAIN CALC ----
OBTAIN_CALC_OUTSIDE_PROCEDURE_TEMPLATE = (
    "*DB2: OBTAIN CALC ignored outside PROCEDURE DIVISION: {line}"
)
REMOVED_OBTAIN_CALC_SELECT_TEMPLATE = (
    "*DB2: Removed OBTAIN CALC SELECT for {record}."
)
DIRECT_UPDATE_COMPOSITE_KEY = (
    "*DB2: Direct UPDATE will use mapped composite key WHERE clause."
)

# ---- OBTAIN FIRST / NEXT ----
OBTAIN_OUTSIDE_PROCEDURE_TEMPLATE = (
    "*DB2: OBTAIN ignored outside PROCEDURE DIVISION: {line}"
)
CONVERTED_OBTAIN_FIRST_TEMPLATE = (
    "*DB2: Converted OBTAIN FIRST {record} WITHIN {set_name}."
)
CONVERTED_OBTAIN_NEXT_TEMPLATE = (
    "*DB2: Converted OBTAIN NEXT {record} WITHIN {set_name}."
)

# ---- FIND FIRST ----
FIND_FIRST_OUTSIDE_PROCEDURE_TEMPLATE = (
    "*DB2: FIND FIRST ignored outside PROCEDURE DIVISION: {line}"
)
CONVERTED_FIND_FIRST_TEMPLATE = (
    "*DB2: Converted FIND FIRST {record} WITHIN {set_name}."
)

# ---- STORE / MODIFY / ERASE ----
STORE_MODIFY_ERASE_OUTSIDE_PROCEDURE_TEMPLATE = (
    "*DB2: {operation} ignored outside PROCEDURE DIVISION: {line}"
)

# ---- Generated PERFORM lines for cursor flow ----
PERFORM_OPEN_CURSOR_TEMPLATE = "PERFORM OPEN-{cursor}."
PERFORM_FETCH_CURSOR_TEMPLATE = "PERFORM FETCH-{cursor}."

# ---- Operation names (used in STORE/MODIFY/ERASE messaging) ----
OPERATION_STORE = "STORE"
OPERATION_MODIFY = "MODIFY"
OPERATION_ERASE = "ERASE"

FINISH_REMOVED_RETRIEVAL = (
    "* DB2: Removed IDMS FINISH; retrieval program is read-only "
    "and needs no COMMIT."
)

TRANSFORMER_MESSAGES = {
    "commit_emitted": (
        "Control statement: FINISH converted to COMMIT (update program)."
    ),
    "commit_suppressed": (
        "Control statement: FINISH removed without COMMIT; retrieval "
        "programs are read-only (EMIT_COMMIT_IN_RETRIEVAL = False)."
    ),
}
TRANSFORMER_MESSAGES["program_kind"] = (
    "Program kind: classified as {kind}; COMMIT policy emit_commit={emit}."
)