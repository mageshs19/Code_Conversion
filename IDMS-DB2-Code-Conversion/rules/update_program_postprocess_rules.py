"""
Rules for update-program COBOL postprocess.

This file contains configurable rule values only.
No regex patterns and no runtime logic belong here.
"""

from __future__ import annotations


UPDATE_POSTPROCESS_RULES = [
    "Apply only to update batch conversion.",
    "Do not change retrieval conversion.",
    "Use parsed COBOL, Copybook, Sheet Mapping, and DCLGEN metadata.",
    "Do not hardcode program-specific copybook or DCLGEN names in logic.",
    "If restart DCLGEN is unavailable, do not fabricate restart SQL.",
    "When restart DCLGEN is available, generate restart SQL from DCLGEN metadata.",
    "Preserve old EOF switch if source program still uses it.",
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

RESTART_DEFAULTS = {
    "phase": "1",
    "status_incomplete": "0",
    "status_complete": "1",
    "retention_days": "7",
}

UPDATE_WORKING_STORAGE_NAMES = {
    "switches_group": "WS-SWITCHES",
    "help_group": "HELP-VARIABLE",
    "restart_record": "WS-RESTART-REC",
    "read_count": "NB-READ",
    "restart_key": "KY-RESTART",
    "input_save_area": "WS-INPUT-KASBONS",
    "commit_counter": "WS-TELLER",
    "input_counter": "WS-NB-INPUT-UPD-I",
    "update_counter": "WS-NB-BFAR-UPD-I",
    "restart_length": "WS-RESTART-LEN",
}

RESTART_DCLGEN_ROLE_TOKENS = {
    "program": ["PROGRAM"],
    "program_fallback": ["NM", "ID", "RS", "PROGRAM"],
    "phase": ["PHASE"],
    "date": ["DA", "CR"],
    "date_fallback": ["DATE"],
    "status": ["CO", "ID"],
    "status_fallback": ["STATUS"],
    "retention": ["DAY"],
    "payload": ["DATA"],
    "payload_length": ["DATA", "LEN"],
    "payload_text": ["DATA", "TEXT"],
}

RESTART_DCLGEN_MIN_SCORE = 4

RESTART_INSERT_QUERYNO = "371"
RESTART_SELECT_QUERYNO = "376"
RESTART_UPDATE_QUERYNO = "398"

GENERATED_UPDATE_COMMENT = "*DB2: Update restart handling generated from DCLGEN."