# LOCATION: rules/lrf_rules.py
# ACTION: CREATE NEW FILE

from __future__ import annotations

LRF_RULES = [
    "Parse the subschema LRF source as metadata only; never execute it.",
    "A logical record is converted only when every element record is mapped.",
    "Do not fabricate a DB2 join when an element record has no Sheet Mapping entry.",
    "OBTAIN path groups drive read logic; ERASE path groups drive delete logic.",
    "Path status codes are diagnostics, not generated COBOL.",
]

# Path-group verbs recognised in the subschema source.
PATH_GROUP_OBTAIN = "OBTAIN"
PATH_GROUP_ERASE = "ERASE"
PATH_GROUP_STORE = "STORE"
PATH_GROUP_MODIFY = "MODIFY"
SUPPORTED_PATH_GROUPS = (
    PATH_GROUP_OBTAIN,
    PATH_GROUP_ERASE,
    PATH_GROUP_STORE,
    PATH_GROUP_MODIFY,
)

# IDMS status codes seen in the path descriptions.
STATUS_OK = "0000"
STATUS_END_OF_AREA = "0307"
STATUS_RECORD_NOT_FOUND = "0326"
STATUS_SET_NOT_EMPTY = "0230"
STATUS_SET_EMPTY = "1601"

# UI / diagnostic labels.
LABEL_LRF = "LRF Subschema"
LABEL_LOGICAL_RECORDS = "Logical Records"
LRF_SOURCE_LABEL = "LRF files"

DIAG_LRF_NOT_UPLOADED = "LRF subschema file not uploaded."
DIAG_LRF_FOLDER_TEMPLATE = "LRF folder: {folder}"
DIAG_LRF_FILE_COUNT_TEMPLATE = "LRF file count: {count}"
DIAG_LRF_FILE_TEMPLATE = "LRF {index}: {path}"
DIAG_LRF_TEXT_LEN_TEMPLATE = "LRF {index} text length: {length}"
DIAG_LRF_TOTAL_RECORDS_TEMPLATE = "LRF logical records parsed: {count}"
DIAG_LRF_PATHS_TEMPLATE = "LRF paths parsed for {lr}: {count}"
DIAG_LRF_PARSE_FAILED_TEMPLATE = "LRF parse failed for {name}: {reason}"

LOG_LRF_FILE_COUNT = "LRF file count: %s"
LOG_LRF_TOTAL_RECORDS = "LRF logical records parsed: %s"

# Validation wording (optional input - warning, never a blocker).
LRF_VALIDATION_MESSAGES = {
    "missing_lrf": (
        "Program uses COPY IDMS LR but no LRF subschema file was supplied. "
        "Logical record access will be skipped and flagged for manual review."
    ),
    "unmapped_element_template": (
        "Logical record {lr}: element record {record} has no Sheet Mapping "
        "entry. Join generation skipped - map this manually."
    ),
}

# LOCATION: rules/lrf_rules.py
# ACTION: APPEND at the end of the file

DIAG_LRF_READ_FAILED_TEMPLATE = "LRF read failed for {name}: {reason}"
DIAG_LRF_PARSED_ZERO = "LRF parsed logical records: 0"
LRF_UPLOAD_LABEL = "Optional LRF Subschema source file or files"
LRF_UPLOAD_HELP = (
    "Upload the subschema source containing ADD LOGICAL RECORD and "
    "ADD PATH-GROUP blocks (for example Sub Schema.txt). Required only "
    "for programs that use COPY IDMS LR."
)
LRF_METRIC_LABEL = "Logical Records"

# LOCATION: rules/lrf_rules.py
# ACTION: APPEND at the end of the file

DIAG_LRF_RECORDS_IN_SCOPE_TEMPLATE = (
    "LRF logical records in scope for this program: {count} ({names})"
)
DIAG_LRF_NO_RECORDS_IN_SCOPE = (
    "LRF logical records in scope for this program: 0. "
    "Logical record access, if any, will be reported for manual review."
)


