from __future__ import annotations

# Batch runner message templates.
#
# All console and diagnostic text lives here so wording stays centralized.
# No regex, no runtime logic, no hardcoded program/record/table names.

# ---- Folder / input validation ----
FOLDER_NOT_FOUND_TEMPLATE = "{label} folder not found: {folder}"
PATH_NOT_FOLDER_TEMPLATE = "{label} path is not a folder: {folder}"
NO_PROGRAM_FILES_TEMPLATE = "No {mode} program files found in: {folder}"
NO_MAPPING_FILES_TEMPLATE = "No mapping sheet files found in: {folder}"
NO_MAPPING_IN_FOLDER_TEMPLATE = "No mapping sheet found in folder: {folder}"
NO_DCLGEN_FILES_TEMPLATE = "No DCLGEN files found in: {folder}"
UNSUPPORTED_MODE_TEMPLATE = "Unsupported batch mode: {mode}"

# Input validation labels.
LABEL_MAPPING_SHEET = "Mapping Sheet"
LABEL_DCLGEN = "DCLgen"
LABEL_COPYBOOK = "Copybook"
LABEL_PROGRAM_TEMPLATE = "{mode} Program"

# ---- Shared input diagnostics ----
DIAG_START_LOAD_SHARED_INPUTS = "START LOAD SHARED INPUTS"
DIAG_MULTIPLE_MAPPING_TEMPLATE = (
    "Multiple mapping sheet files found. Using first sorted file: {first}. "
    "All found: {names}"
)
DIAG_MAPPING_FOLDER_TEMPLATE = "Mapping Sheet folder: {folder}"
DIAG_MAPPING_SELECTED_TEMPLATE = "Mapping Sheet selected: {path}"
DIAG_MAPPING_ROWS_TEMPLATE = "Mapping Sheet rows: {count}"
DIAG_DCLGEN_FOLDER_TEMPLATE = "DCLGEN folder: {folder}"
DIAG_DCLGEN_FILE_COUNT_TEMPLATE = "DCLGEN file count: {count}"
DIAG_DCLGEN_FILE_TEMPLATE = "DCLGEN {index}: {path}"
DIAG_DCLGEN_TEXT_LEN_TEMPLATE = "DCLGEN {index} text length: {length}"
DIAG_DCLGEN_TOTAL_COLUMNS_TEMPLATE = "DCLGEN total columns: {count}"
DIAG_COPYBOOK_FOLDER_TEMPLATE = "Copybook folder: {folder}"
DIAG_COPYBOOK_FILE_COUNT_TEMPLATE = "Copybook file count: {count}"
DIAG_COPYBOOK_FILE_TEMPLATE = "Copybook {index}: {path}"
DIAG_COPYBOOK_TEXT_LEN_TEMPLATE = "Copybook {index} text length: {length}"
DIAG_COPYBOOK_TOTAL_FIELDS_TEMPLATE = "Copybook total fields: {count}"

# Source label used when parsing copybook text.
COPYBOOK_SOURCE_LABEL = "Copybook files"
DCLGEN_SOURCE_LABEL_TEMPLATE = "DCLGEN file {index}"

# ---- Per-program conversion diagnostics ----
DIAG_SOURCE_FILE_TEMPLATE = "{mode} COBOL source file: {path}"
DIAG_SOURCE_LEN_TEMPLATE = "{mode} COBOL source text length: {length}"

# ---- Update postprocess diagnostics ----
DIAG_UPDATE_ENHANCEMENT_DONE = "Update postprocess enhancement completed."
DIAG_UPDATE_AUDIT_MOVES = (
    "Update audit moves: inserted TS_UPDATE / USER-ID host moves before "
    "UPDATE SQL."
)
DIAG_UPDATE_SKIPPED_TEMPLATE = (
    "Update postprocess enhancement skipped. Original converted COBOL will "
    "be written. Reason: {reason}"
)

# ---- Result reporting ----
LOG_CONVERSION_COMPLETED_TEMPLATE = "{mode} conversion completed."
LOG_INPUT_PROGRAM_TEMPLATE = "Input program: {path}"
LOG_OUTPUT_FILE_TEMPLATE = "Output file: {path}"

PRINT_GENERATION_COMPLETED_TEMPLATE = "{mode} DB2 COBOL generation completed."
PRINT_INPUT_PROGRAM_TEMPLATE = "Input program: {path}"
PRINT_OUTPUT_CREATED_TEMPLATE = "Output file created: {path}"

HEADER_VALIDATION_MESSAGES = "Validation Messages"
HEADER_DIAGNOSTICS = "Diagnostics"
HEADER_BATCH_INPUT_SUMMARY = "Batch Input Summary"
NO_VALIDATION_MESSAGES = "No validation messages."
BULLET_TEMPLATE = "- {text}"

# ---- Batch summary lines ----
SUMMARY_PROJECT_ROOT_TEMPLATE = "Project Root     : {value}"
SUMMARY_SRC_DIR_TEMPLATE = "SRC Directory    : {value}"
SUMMARY_MODE_TEMPLATE = "Mode             : {value}"
SUMMARY_MAPPING_FOLDER_TEMPLATE = "Mapping Folder   : {value}"
SUMMARY_PROGRAM_FOLDER_TEMPLATE = "Program Folder   : {value}"
SUMMARY_PROGRAM_COUNT_TEMPLATE = "Program Count    : {value}"
SUMMARY_OUTPUT_FOLDER_TEMPLATE = "Output Folder    : {value}"
SUMMARY_TARGET_PROGRAM_ID_TEMPLATE = "Target PROGRAM-ID: {value}"
PRESERVE_SOURCE_LABEL = "(preserve source)"