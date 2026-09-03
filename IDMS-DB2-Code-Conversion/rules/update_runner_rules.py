from __future__ import annotations

# Update runner rule constants. Constants only. No regex, no logic.

UPDATE_RUNNER_RULES = [
    "Derive the target PROGRAM-ID from the source (VM...BD... -> VMDZ...).",
    "Preserve the source PROGRAM-ID when no PROGRAM-ID is detected.",
    "Load Sheet Mapping, DCLGEN, and Copybook inputs once and share them.",
    "Exactly one mapping sheet must be present for update runs.",
    "Do not hardcode program names, DB2 tables, columns, or host variables.",
]

AUTO_FIX_PIC_LENGTH_MISMATCHES_DEFAULT = False
OUTPUT_TIMESTAMP_FORMAT = "%d-%m-%Y_%H%M%S"
OUTPUT_FILE_EXTENSION = ".cbl"
OUTPUT_FILE_NAME_TEMPLATE = "{stem}_{timestamp}{extension}"
COBOL_TEXT_ENCODING = "utf-8"
UPDATE_LOGGER_NAME = "idms_db2_update_conversion"