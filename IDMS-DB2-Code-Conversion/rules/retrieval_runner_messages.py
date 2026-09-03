from __future__ import annotations

# Retrieval runner message templates.
#
# All console and diagnostic text lives here so wording stays centralized.
# No regex, no runtime logic, no hardcoded program/record/table names.

# ---- Validation labels ----
LABEL_MAPPING_SHEET = "Mapping Sheet"
LABEL_SHEET_MAPPING = "Sheet Mapping"
LABEL_RETRIEVAL_PROGRAM = "Retrieval Program"
LABEL_DCLGEN_TEMPLATE = "DCLGEN {index}"
LABEL_COPYBOOK_TEMPLATE = "Copybook {index}"
LABEL_RETRIEVAL_PROGRAM_TEMPLATE = "Retrieval Program {index}"

# ---- Validation errors ----
FILE_NOT_FOUND_TEMPLATE = "{label} file not found: {path}"
PATH_NOT_FILE_TEMPLATE = "{label} path is not a file: {path}"
FOLDER_NOT_FOUND_TEMPLATE = "{label} folder not found: {path}"
PATH_NOT_FOLDER_TEMPLATE = "{label} path is not a folder: {path}"
NO_MAPPING_FILE_TEMPLATE = "No mapping sheet file found in: {folder}"
NO_PROGRAM_FILE_TEMPLATE = "No retrieval program file found in: {folder}"
NO_DCLGEN_CANDIDATE_TEMPLATE = (
    "At least one DCLGEN file path is required. No DCLGEN candidate file was "
    "found. Searched:\n{searched}"
)

# ---- Shared input diagnostics ----
DIAG_START_LOAD_INPUTS = "START LOAD INPUTS"
DIAG_MAPPING_FOLDER_TEMPLATE = "Sheet Mapping folder: {folder}"
DIAG_MAPPING_SELECTED_TEMPLATE = "Sheet Mapping selected: {path}"
DIAG_MAPPING_ROWS_TEMPLATE = "Sheet Mapping rows: {count}"
DIAG_DCLGEN_FILE_COUNT_TEMPLATE = "DCLGEN file count: {count}"
DIAG_DCLGEN_FILE_TEMPLATE = "DCLGEN {index}: {path}"
DIAG_DCLGEN_TEXT_LEN_TEMPLATE = "DCLGEN {index} text length: {length}"
DIAG_DCLGEN_TOTAL_COLUMNS_TEMPLATE = "DCLGEN total columns: {count}"
DIAG_COPYBOOK_FILE_COUNT_TEMPLATE = "Copybook file count: {count}"
DIAG_COPYBOOK_FILE_TEMPLATE = "Copybook {index}: {path}"
DIAG_COPYBOOK_TEXT_LEN_TEMPLATE = "Copybook {index} text length: {length}"
DIAG_COPYBOOK_TOTAL_FIELDS_TEMPLATE = "Copybook total fields: {count}"

# Parser source labels.
COPYBOOK_SOURCE_LABEL = "Copybook files"
DCLGEN_SOURCE_LABEL_TEMPLATE = "DCLGEN file {index}"

# ---- Log format strings (printf-style for logger) ----
LOG_MAPPING_SELECTED = "Sheet Mapping selected: %s"
LOG_MAPPING_ROWS = "Sheet Mapping rows: %s"
LOG_DCLGEN_FILE_COUNT = "DCLGEN file count: %s"
LOG_DCLGEN_FILE = "DCLGEN %s: %s"
LOG_DCLGEN_TEXT_LEN = "DCLGEN %s text length: %s"
LOG_DCLGEN_TOTAL_COLUMNS = "DCLGEN total columns: %s"
LOG_COPYBOOK_FILE_COUNT = "Copybook file count: %s"
LOG_COPYBOOK_FILE = "Copybook %s: %s"
LOG_COPYBOOK_TEXT_LEN = "Copybook %s text length: %s"
LOG_COPYBOOK_TOTAL_FIELDS = "Copybook total fields: %s"

# ---- Per-program conversion ----
DIAG_SOURCE_FILE_TEMPLATE = "IDMS COBOL source file: {path}"
DIAG_SOURCE_LEN_TEMPLATE = "IDMS COBOL source text length: {length}"
DIAG_DERIVED_PROGRAM_ID_TEMPLATE = "Derived target PROGRAM-ID: {value}"

LOG_SOURCE_FILE = "IDMS COBOL source file: %s"
LOG_SOURCE_LEN = "IDMS COBOL source text length: %s"
LOG_DERIVED_PROGRAM_ID = "Derived target PROGRAM-ID: %s"
LOG_GENERATION_COMPLETED = "Retrieval DB2 COBOL generation completed."
LOG_OUTPUT_CREATED = "Output file created: %s"

PRESERVE_SOURCE_LABEL = "(preserve source)"

# ---- Console output ----
PRINT_GENERATION_COMPLETED = "Retrieval DB2 COBOL generation completed."
PRINT_INPUT_PROGRAM_TEMPLATE = "Input program: {path}"
PRINT_OUTPUT_CREATED_TEMPLATE = "Output file created: {path}"

HEADER_INPUT_SUMMARY = "Input Summary"
HEADER_SELECTED_INPUT_FILES = "Selected Input Files"
HEADER_VALIDATION_MESSAGES = "Validation Messages"
HEADER_DIAGNOSTICS = "Diagnostics"
HEADER_RETRIEVAL_BATCH_SUMMARY = "Retrieval Batch Summary"

RULE_INPUT_SUMMARY = "-------------"
RULE_SELECTED_INPUT_FILES = "--------------------"
RULE_VALIDATION_MESSAGES = "-------------------"
RULE_DIAGNOSTICS = "-----------"
RULE_RETRIEVAL_BATCH_SUMMARY = "-----------------------"

SUMMARY_PROJECT_ROOT_TEMPLATE = "Project Root       : {value}"
SUMMARY_SRC_DIR_TEMPLATE = "SRC Directory      : {value}"
SUMMARY_SHEET_ROWS_TEMPLATE = "Sheet Mapping Rows : {value}"
SUMMARY_DCLGEN_COLUMNS_TEMPLATE = "DCLGEN Columns     : {value}"
SUMMARY_COPYBOOK_FIELDS_TEMPLATE = "Copybook Fields    : {value}"
SUMMARY_COBOL_LEN_TEMPLATE = "COBOL Text Length  : {value}"
SUMMARY_TARGET_PROGRAM_ID_TEMPLATE = "Target PROGRAM-ID  : {value}"

SELECTED_SHEET_MAPPING_TEMPLATE = "Sheet Mapping       : {value}"
SELECTED_COBOL_SOURCE_TEMPLATE = "IDMS COBOL Source   : {value}"
SELECTED_DCLGEN_HEADER = "DCLGEN Files:"
SELECTED_COPYBOOK_HEADER = "Copybook Files:"
SELECTED_COPYBOOK_NONE = "Copybook Files      : None"
SELECTED_PATH_BULLET_TEMPLATE = " - {value}"

BATCH_PROGRAM_FOLDER_TEMPLATE = "Program Folder   : {value}"
BATCH_PROGRAM_COUNT_TEMPLATE = "Program Count    : {value}"
BATCH_OUTPUT_FOLDER_TEMPLATE = "Output Folder    : {value}"

NO_VALIDATION_MESSAGES = "No validation messages."
BULLET_TEMPLATE = "- {text}"