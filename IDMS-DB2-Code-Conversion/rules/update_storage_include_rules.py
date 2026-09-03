from __future__ import annotations

# Update storage/include manager constants. Constants only.
# No regex, no runtime logic, no program/record/table names.

# Includes that must never be auto-injected as DCLGEN includes.
EXCLUDED_INCLUDE_NAMES = frozenset({"GEN", "SQLCA", "SQLERRWS", "SQLERROR"})

# DCLGEN host-group prefix.
DCL_GROUP_PREFIX = "DCL"

# Working-storage anchor lines (checked before injecting).
WS_ANCHOR_01_TEMPLATE = "01 {group}."
DATE_WS_ANCHORS = ("01 WS-DATUMVELDEN.", "01  WS-DATUMVELDEN.")

# CS-PROGRAM 77-level replacement body (program-id substituted).
CS_PROGRAM_77_TEMPLATE = (
    "{prefix}77  CS-PROGRAM                 PIC X(8) VALUE '{program_id}'."
)
PROGRAM_NAME_MOVE_REPLACEMENT_TEMPLATE = "MOVE '{program_id}' TO PROGRAM-NAME."

# --- Diagnostics / skip messages ---
SKIP_DATA_DIVISION_WS = (
    "Safe DATA DIVISION insertion point not found. Skipped update restart "
    "working-storage injection."
)
SKIP_DATA_DIVISION_DATE_WS = (
    "Safe DATA DIVISION insertion point not found. Skipped manual-style date "
    "working-storage injection."
)
SKIP_DATA_DIVISION_DCLGEN_TEMPLATE = (
    "Safe DATA DIVISION insertion point not found. Skipped DCLGEN include: "
    "{include}"
)
SKIP_DATA_DIVISION_REFERENCED = (
    "Safe DATA DIVISION insertion point not found. Skipped referenced DCLGEN "
    "include injection."
)
SKIP_DATA_DIVISION_COPYBOOK_TEMPLATE = (
    "Safe DATA DIVISION insertion point not found. Skipped input copybook "
    "include: {include}"
)
RESTART_DCLGEN_UNAVAILABLE = (
    "Restart DCLGEN not available. Skipped restart include and restart SQL "
    "generation."
)
DCLGEN_INCLUDE_EXISTS_TEMPLATE = "DCLGEN include already exists: {include}"
DCLGEN_INCLUDE_INJECTED_TEMPLATE = "Injected DCLGEN include: {include}"
REFERENCED_DCLGEN_INJECTED_TEMPLATE = "{base}: {include}"
COPY_EXISTS_TEMPLATE = "{base}: {include}"
COPY_EXISTS_BY_RECORD_TEMPLATE = (
    "Input copybook include already exists by record name: {record}"
)
COPY_INJECTED_TEMPLATE = "{base}: {include}"