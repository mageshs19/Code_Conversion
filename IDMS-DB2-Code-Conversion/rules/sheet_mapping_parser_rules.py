from __future__ import annotations

# Sheet Mapping parser constants. Constants only.
# No regex, no parser logic, no column/alias names (those live in catalogs).

# --- File handling ---
CSV_TEXT_ENCODING = "utf-8-sig"
XLSX_SUFFIX = ".xlsx"
LEGACY_XLS_SUFFIX = ".xls"

# --- Magic numbers ---
CSV_SAMPLE_LENGTH = 500       # chars of CSV shown in the sample diagnostic
HEADER_SCAN_ROW_LIMIT = 100   # rows scanned when locating the header row
HEADER_DEBUG_ROW_LIMIT = 10   # rows for which normalized cells are logged

# --- Diagnostic messages ---
DIAG_NO_FILE = "No Sheet Mapping file supplied."
DIAG_FILE_NAME_TEMPLATE = "Sheet Mapping file name: {name}"
DIAG_FILE_SIZE_TEMPLATE = "Sheet Mapping file size bytes: {size}"
DIAG_UNSUPPORTED_XLS = (
    "Unsupported .xls file detected. Save the file as .xlsx or .csv."
)
DIAG_CSV_DECODED_LEN_TEMPLATE = "CSV/text decoded length: {length}"
DIAG_CSV_SAMPLE_TEMPLATE = "CSV/text sample: {sample}"
DIAG_CSV_EMPTY = "CSV/text Sheet Mapping is empty."
DIAG_CSV_NO_ROWS = "CSV/text Sheet Mapping has no rows."
DIAG_CSV_HEADERS_TEMPLATE = "CSV detected headers: {headers}"
DIAG_CSV_USEFUL_ROWS_TEMPLATE = "CSV parsed useful rows: {count}"
DIAG_XLSX_EMPTY = "XLSX Sheet Mapping is empty."
DIAG_XLSX_USEFUL_ROWS_TEMPLATE = "XLSX parsed useful rows: {count}"
DIAG_SHEET_NO_HEADER_TEMPLATE = (
    "Sheet {sheet}: no Sheet Mapping header row detected."
)
DIAG_SHEET_USEFUL_ROWS_TEMPLATE = "Sheet {sheet}: parsed useful rows: {count}"
DIAG_SHEET_NORMALIZED_CELLS_TEMPLATE = (
    "Sheet {sheet}: row {index} normalized cells: {cells}"
)

# --- Population diagnostic spec ---
# Each entry: (label, [row-attribute names]); a row counts if ANY attr is set.
POPULATION_DIAGNOSTIC_SPEC = [
    ("Sheet Mapping populated Cobol Record IDMS rows", ["cobol_record_idms"]),
    (
        "Sheet Mapping populated source field rows",
        ["cobol_zone", "reference_field_name_copybook"],
    ),
    (
        "Sheet Mapping populated DB2 table rows",
        ["new_db2_record", "cross_application_db2_table"],
    ),
    (
        "Sheet Mapping populated DB2 column rows",
        ["new_db2_field_name", "cross_application_db2_field_name"],
    ),
]

# Useful-context diagnostic: each group must have at least one populated attr.
USEFUL_CONTEXT_LABEL = "Sheet Mapping useful source-to-target rows"
USEFUL_CONTEXT_GROUPS = [
    ["cobol_record_idms"],
    ["cobol_zone", "reference_field_name_copybook"],
    ["new_db2_record", "cross_application_db2_table"],
    ["new_db2_field_name", "cross_application_db2_field_name"],
]