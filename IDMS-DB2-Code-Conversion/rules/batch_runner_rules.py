from __future__ import annotations

# Batch runner rule constants.
#
# Constants only. No regex, no runtime logic, no program/record/table names.
# Change a value here and it reflects across every batch runner.

BATCH_RUNNER_RULES = [
    "Mapping Sheet is selected from the mapping folder (first sorted file).",
    "DCLGEN and Copybook inputs are loaded once and shared across programs.",
    "Target PROGRAM-ID comes from the environment, then the mode default.",
    "Do not hardcode program names, DB2 tables, columns, or host variables.",
]

# Supported batch mode names.
BATCH_MODE_UPDATE = "UPDATE"
BATCH_MODE_RETRIEVAL = "RETRIEVAL"

# Environment variable key that overrides the target PROGRAM-ID.
TARGET_PROGRAM_ID_ENV_KEY = "TARGET_PROGRAM_ID"

# Converter behavior defaults.
AUTO_FIX_PIC_LENGTH_MISMATCHES_DEFAULT = False

# Output file naming.
OUTPUT_TIMESTAMP_FORMAT = "%d-%m-%Y_%H%M%S"
OUTPUT_FILE_EXTENSION = ".cbl"
OUTPUT_FILE_NAME_TEMPLATE = "{stem}_{timestamp}{extension}"

# Text encoding used when reading/writing COBOL files.
COBOL_TEXT_ENCODING = "utf-8"