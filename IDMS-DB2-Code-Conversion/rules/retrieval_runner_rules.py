from __future__ import annotations

# Retrieval runner rule constants.
#
# Constants only. No regex, no runtime logic, no program/record/table names.
# Change a value here and it reflects across the retrieval runner.

RETRIEVAL_RUNNER_RULES = [
    "Derive the target PROGRAM-ID from the source (VM...BD... -> VMDZ...).",
    "Preserve the source PROGRAM-ID when no PROGRAM-ID is detected.",
    "Load Sheet Mapping, DCLGEN, and Copybook inputs once and share them.",
    "Do not hardcode program names, DB2 tables, columns, or host variables.",
]

# Converter behavior defaults.
AUTO_FIX_PIC_LENGTH_MISMATCHES_DEFAULT = False

# Output file naming.
OUTPUT_TIMESTAMP_FORMAT = "%d-%m-%Y_%H%M%S"
OUTPUT_FILE_EXTENSION = ".cbl"
OUTPUT_FILE_NAME_TEMPLATE = "{stem}_{timestamp}{extension}"

# Text encoding used when reading/writing COBOL files.
COBOL_TEXT_ENCODING = "utf-8"

# Logger name for the retrieval conversion run.
RETRIEVAL_LOGGER_NAME = "idms_db2_retrieval_conversion"