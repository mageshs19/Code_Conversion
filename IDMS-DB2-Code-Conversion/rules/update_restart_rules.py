from __future__ import annotations

"""
Rules for update-program restart postprocess.

This module contains configurable rule constants only.
No parser logic, generator logic, service logic, file paths, program names,
copybook names, DB2 table names, DCLGEN names, or host variables should be
hardcoded here.
"""

UPDATE_RESTART_RULES = [
    "Apply only in update-program postprocess.",
    "Do not touch retrieval conversion.",
    "Use parsed COBOL source, parsed Copybook fields, and parsed DCLGEN columns.",
    "Do not hardcode program-specific copybook names.",
    "Do not hardcode program-specific DCLGEN names.",
    "Do not hardcode DB2 restart table names in parser, service, or enhancer logic.",
    "Do not hardcode restart host variables in parser, service, or enhancer logic.",
    "Do not generate restart SQL unless restart DCLGEN metadata is available.",
    "Replace legacy IDMS restart-control flow only when restart DCLGEN is resolved.",
    "Preserve COBOL business logic unless update restart flow is explicitly replaced.",
    "For VARCHAR restart payload fields, derive generated LEN and TEXT subfields from the parsed payload group when needed.",
]

RESTART_PARAGRAPH_NAMES = {
    "control": "700-RESTART-CONTROL",
    "restart_found": "710-JOB-IS-RESTART",
    "write_restart": "720-WRITE-RESTART-REC",
    "commit": "800-PROCESS-COMMIT",
    "select": "700-SELECT-DZ01RSTV",
    "update": "700-UPDATE-DZ01RSTV",
    "insert": "700-INSERT-DZ01RSTV",
    "abend": "810000-CALL-USERABEN",
}

RESTART_STATUS_INCOMPLETE = "0"
RESTART_STATUS_COMPLETE = "1"
RESTART_DEFAULT_PHASE = "1"
RESTART_RETENTION_DAYS = "7"

RESTART_SELECT_QUERYNO = "376"
RESTART_UPDATE_QUERYNO = "398"
RESTART_INSERT_QUERYNO = "413"

RESTART_DCLGEN_MIN_SCORE = 10

RESTART_DCLGEN_ROLE_TOKENS = {
    "program": ["NM", "ID", "RS", "PROGRAM"],
    "program_fallback": ["PROGRAM"],
    "phase": ["NB", "ID", "RS", "PHASE"],
    "phase_fallback": ["PHASE"],
    "date": ["DA", "CR", "RS"],
    "date_fallback": ["DATE"],
    "status": ["CO", "ID", "RS"],
    "status_fallback": ["STATUS"],
    "retention": ["NB", "DAY", "RS"],
    "retention_fallback": ["DAY"],
    "payload": ["TE", "CH", "RS", "DATA"],
    "payload_fallback": ["DATA"],
    "payload_length": ["TE", "CH", "RS", "DATA", "LEN"],
    "payload_length_fallback": ["DATA", "LEN"],
    "payload_text": ["TE", "CH", "RS", "DATA", "TEXT"],
    "payload_text_fallback": ["DATA", "TEXT"],
}

RESTART_VARCHAR_SUFFIXES = {
    "length": "-LEN",
    "text": "-TEXT",
}

UPDATE_RESTART_WS_NAMES = {
    "switch_group": "WS-SWITCHES",
    "help_group": "HELP-VARIABLE",
    "restart_record": "WS-RESTART-REC",
    "read_count": "NB-READ",
    "restart_key": "KY-RESTART",
    "input_save_area": "WS-INPUT-KASBONS",
    "commit_counter": "WS-TELLER",
    "input_counter": "WS-NB-INPUT-UPD-I",
    "update_counter": "WS-NB-BFAR-UPD-I",
    "restart_len": "WS-RESTART-LEN",
}

UPDATE_LEGACY_RESTART_WS_NAMES = (
    "CTR-REC",
    "SW-EOF",
    "SW-RECAB",
)

UPDATE_STANDARD_DATE_WS_LINES = [
    "01  WS-DATUMVELDEN.",
    "    03  DA-YYMMDD.",
    "        05  YY                 PIC 99            VALUE ZERO.",
    "        05  MM                 PIC 99            VALUE ZERO.",
    "        05  DD                 PIC 99            VALUE ZERO.",
    "    03  DA-DDMMCCYY.",
    "        05  DD                 PIC 99            VALUE ZERO.",
    "        05  MM                 PIC 99            VALUE ZERO.",
    "        05  CC                 PIC 99            VALUE ZERO.",
    "        05  YY                 PIC 99            VALUE ZERO.",
    "    03  DA-CCYYMMDD.",
    "        05  CC                 PIC 99            VALUE ZERO.",
    "        05  YY                 PIC 99            VALUE ZERO.",
    "        05  MM                 PIC 99            VALUE ZERO.",
    "        05  DD                 PIC 99            VALUE ZERO.",
    "    03  DA-CCYYMMDD-R REDEFINES DA-CCYYMMDD.",
    "        05  CCYY               PIC 9999.",
    "        05  MM                 PIC 99.",
    "        05  DD                 PIC 99.",
    "    02  DA-DD-MM-CCYY.",
    "        03  DD                 PIC 9(02).",
    "        03  TE-MARKER5         PIC X             VALUE '.'.",
    "        03  MM                 PIC 9(02).",
    "        03  TE-MARKER6         PIC X             VALUE '.'.",
    "        03  CCYY               PIC 9(04).",
]

UPDATE_MAIN_DATE_INITIALIZATION_LINES = [
    "MOVE ZEROES TO DA-CCYYMMDD.",
    "MOVE DATE-YMD8 TO DA-CCYYMMDD.",
    "MOVE CORR DA-CCYYMMDD-R TO DA-DD-MM-CCYY.",
]

UPDATE_SUMMARY_DISPLAY_TEMPLATES = [
    "DISPLAY 'NUMBER OF RECORDS PROCESSED: ' {input_counter}.",
    "DISPLAY 'NUMBER OF UPDATE RECORDS   : ' {update_counter}.",
]

UPDATE_SQL_PARAGRAPH_PREFIX = "1100-UPDATE"
UPDATE_COMMIT_THRESHOLD = 99

UPDATE_RESTART_DIAGNOSTICS = {
    "start": "START UPDATE PROGRAM POST-PROCESS ENHANCEMENT",
    "end": "END UPDATE PROGRAM POST-PROCESS ENHANCEMENT",
    "context_failed": (
        "Postprocess context resolution failed. Generated COBOL left unchanged."
    ),
    "ws_exists": "Working-storage support already exists.",
    "ws_injected": "Injected COBOL-standard update restart working-storage.",
    "copy_exists": "Input copybook include already exists.",
    "copy_injected": "Injected input copybook include.",
    "dclgen_exists": "Restart DCLGEN include already exists.",
    "dclgen_injected": "Injected restart DCLGEN include.",
    "referenced_dclgen_injected": "Injected referenced DCLGEN include.",
    "date_ws_exists": "Manual-style date working-storage already exists.",
    "date_ws_injected": "Injected manual-style date working-storage.",
    "legacy_ws_removed": "Removed legacy update restart working-storage declarations.",
    "program_name_normalized": "Normalized PROGRAM-NAME move to resolved PROGRAM-ID.",
    "main_init_added": "Added standard update main initialization.",
    "summary_display_added": "Added standard update summary DISPLAY statements.",
    "read_replaced": "Replaced READ-FLAT-FILE with copybook-standard implementation.",
    "read_added": "Added READ-FLAT-FILE copybook-standard implementation.",
    "restart_missing": "Restart DCLGEN unresolved. Restart paragraphs skipped.",
    "restart_inserted": "Injected standard restart-table paragraphs.",
    "legacy_replaced": "Replaced legacy active restart main flow with standard update restart flow.",
    "legacy_not_found": "Legacy active restart main flow not found.",
    "malformed_sqlerror_fixed": "Fixed malformed PERFORM SQLERROR.END-EVALUATE line.",
    "business_update_extracted": "Extracted inline business UPDATE SQL into standard update paragraph.",
    "business_update_not_found": "Inline business UPDATE SQL block not found for extraction.",
}

__all__ = [
    "UPDATE_RESTART_RULES",
    "RESTART_PARAGRAPH_NAMES",
    "RESTART_STATUS_INCOMPLETE",
    "RESTART_STATUS_COMPLETE",
    "RESTART_DEFAULT_PHASE",
    "RESTART_RETENTION_DAYS",
    "RESTART_SELECT_QUERYNO",
    "RESTART_UPDATE_QUERYNO",
    "RESTART_INSERT_QUERYNO",
    "RESTART_DCLGEN_MIN_SCORE",
    "RESTART_DCLGEN_ROLE_TOKENS",
    "RESTART_VARCHAR_SUFFIXES",
    "UPDATE_RESTART_WS_NAMES",
    "UPDATE_LEGACY_RESTART_WS_NAMES",
    "UPDATE_STANDARD_DATE_WS_LINES",
    "UPDATE_MAIN_DATE_INITIALIZATION_LINES",
    "UPDATE_SUMMARY_DISPLAY_TEMPLATES",
    "UPDATE_SQL_PARAGRAPH_PREFIX",
    "UPDATE_COMMIT_THRESHOLD",
    "UPDATE_RESTART_DIAGNOSTICS",
]

# --- Update main flow rewriter constants (appended) ---

# Fixed-format geometry.
MAIN_FLOW_FIXED_BODY_WIDTH = 65
MAIN_FLOW_SEQUENCE_WIDTH = 6
MAIN_FLOW_INDICATOR_COLUMN = 7
MAIN_FLOW_BODY_START = 7
MAIN_FLOW_BODY_END = 72
MAIN_FLOW_FULL_WIDTH = 72
MAIN_FLOW_TOTAL_WIDTH = 80
MAIN_FLOW_RIGHT_SEQUENCE_WIDTH = 8
MAIN_FLOW_AREA_B_INDENT = "    "
MAIN_FLOW_COMMENT_INDICATORS = ("*", "/", "D")

# COBOL tokens.
MAIN_FLOW_READ_FLAT_FILE_PARAGRAPH = "READ-FLAT-FILE"
MAIN_FLOW_TOKEN_CLOSE = "CLOSE "
MAIN_FLOW_LONE_PERIOD = "."

# Generated bodies.
MAIN_FLOW_PERFORM_READ_BODY = "PERFORM READ-FLAT-FILE"
MAIN_FLOW_PERFORM_READ_BODY_DOT = "PERFORM READ-FLAT-FILE."
MAIN_FLOW_SET_NOT_EOF_TEMPLATE = "SET {record}-NOT-EOF TO TRUE."
MAIN_FLOW_INITIALIZE_HELP_TEMPLATE = "INITIALIZE {help_group}."

# Main restart flow template lines (dynamic values via .format()).
MAIN_FLOW_RESTART_TEMPLATE_LINES = [
    "",
    "    PERFORM {control}.",
    "",
    "    PERFORM READ-FLAT-FILE.",
    "    PERFORM {process_paragraph} UNTIL {record}-EOF.",
    "",
    "    PERFORM {commit}.",
    "",
    "    CLOSE {file_name}.",
    "",
]

# Legacy restart detection tokens.
MAIN_FLOW_LEGACY_RESTART_TOKENS = (
    "SW-RECAB",
    "CTR-REC",
    "FFRECAB",
    "NS-REC-FF-IN",
    "READ-FLAT-FILE VARYING",
    "INSERT INTO",
    "DZ01RST",
)

# Restart / utility paragraph-number prefixes to skip when resolving the
# business processing paragraph.
MAIN_FLOW_RESTART_PARAGRAPH_PREFIXES = (
    "600-",
    "700-",
    "710-",
    "720-",
    "800-",
    "810000-",
)

# Region look-back windows.
MAIN_FLOW_OPEN_LOOKBACK = 20
MAIN_FLOW_CLOSE_LOOKBACK = 10

# --- Main flow skip/status diagnostics (appended, not already present) ---
MAIN_FLOW_DIAGNOSTICS = {
    "dclgen_unresolved": (
        "Restart DCLGEN unresolved. Legacy restart main flow left unchanged."
    ),
    "open_not_found": (
        "OPEN INPUT line not found. Legacy restart main flow replacement "
        "skipped."
    ),
    "stop_not_found": (
        "STOP RUN line not found. Legacy restart main flow replacement "
        "skipped."
    ),
    "legacy_not_found": (
        "Legacy restart statements not found between OPEN INPUT and STOP RUN. "
        "Main flow replacement skipped."
    ),
    "process_unresolved": (
        "Processing paragraph could not be resolved. Legacy restart main flow "
        "replacement skipped."
    ),
    "process_empty": (
        "Processing paragraph is empty. Skipped READ-FLAT-FILE insertion into "
        "process paragraph."
    ),
    "process_not_found": (
        "Processing paragraph not found: {paragraph}. Skipped READ-FLAT-FILE "
        "insertion into process paragraph."
    ),
    "already_reads_next": (
        "Processing paragraph already reads next input record: {paragraph}."
    ),
    "no_insertion_point": (
        "Safe insertion point not found in processing paragraph: {paragraph}."
    ),
    "read_inserted": (
        "Inserted READ-FLAT-FILE at end of processing paragraph: {paragraph}."
    ),
}
# --- Restart DCLGEN role-key spec (appended) ---
#
# Each role that resolves a (column, field) pair from the same token set.
# Format: role_name -> (token_key, fallback_token_key)
# The builder loops over this map so no per-role code repetition is needed.

RESTART_ROLE_COLUMN_FIELD_SPEC = {
    "program": ("program", "program_fallback"),
    "phase": ("phase", "phase_fallback"),
    "date": ("date", "date_fallback"),
    "status": ("status", "status_fallback"),
    "retention": ("retention", "retention_fallback"),
}

# Payload resolves only a column (no field pair).
RESTART_PAYLOAD_TOKEN_KEY = "payload"
RESTART_PAYLOAD_FALLBACK_TOKEN_KEY = "payload_fallback"

# Payload child field specs: (token_key, fallback_token_key, suffix_key).
RESTART_PAYLOAD_LENGTH_SPEC = (
    "payload_length",
    "payload_length_fallback",
    "length",
)
RESTART_PAYLOAD_TEXT_SPEC = (
    "payload_text",
    "payload_text_fallback",
    "text",
)