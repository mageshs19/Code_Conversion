# LOCATION: rules/validation_display_rules.py
# ACTION: REPLACE ENTIRE FILE

"""Validation and diagnostics presentation rules.

Constants only. No regex, no runtime logic, no program / record / table
names.

WHY THIS EXISTS
---------------
`validation_messages` is a single flat list that every generator and
composer appends to. It mixes three very different things:

  1. INPUT and MAPPING failures    - the run produced unusable output
  2. SKIPS and GAPS                - the run needs a human decision
  3. PASS NARRATION                - a composer reporting normal work

The Validation tab rendered all three through st.warning(), so eighty
lines of "a pass did its job" drowned the two lines that mattered.

Classification is PREFIX-FIRST and keyword-second, so a new composer that
follows the existing "Prefix: text" convention is categorised correctly
without touching this file.
"""

from __future__ import annotations

# =====================================================================
# Severities
# =====================================================================
SEVERITY_ERROR = "Error"
SEVERITY_WARNING = "Warning"
SEVERITY_INFO = "Info"

SEVERITY_ORDER = (SEVERITY_ERROR, SEVERITY_WARNING, SEVERITY_INFO)

SEVERITY_ICONS = {
    SEVERITY_ERROR: "ERROR",
    SEVERITY_WARNING: "WARN",
    SEVERITY_INFO: "INFO",
}

# =====================================================================
# Prefix -> severity
#
# Matched against the text before the first colon, case-insensitively.
# A source that always reports failures is classified once here rather
# than by scanning its wording.
# =====================================================================
ERROR_PREFIXES = (
    "mapping validation",
    "production validation",
    "input validation",
    "validation error",
)

WARNING_PREFIXES = (
    "update restart skip",
    "db2 warning",
)

INFO_PREFIXES = (
    "cleanup",
    "safety",
    "counters",
    # MappingScopeFilter rewrites a workbook gap on a table THIS program
    # does not reference. It is a note about the Sheet Mapping, not a
    # conversion failure, so it belongs in the log rather than the Errors
    # band. Without this entry the "Mapping scope" prefix would fall
    # through to the keyword pass and be caught by "no usable".
    "mapping scope",
    "output write",
    "procedure indent",
    "sequence artifact",
    "db2 infrastructure",
    "db2 cursor paragraphs",
    "cursor declaration",
    "cursor join",
    "cursor flow",
    "timestamp generator",
    "sqlerror",
    "program flow analyzer",
    "update sql cleanup",
    "update structure feedback",
    "field reference",
)

# =====================================================================
# Keyword -> severity
#
# Applied only when the prefix does not decide. Order matters: the first
# matching tuple wins.
# =====================================================================
ERROR_KEYWORDS = (
    "is required",
    "must contain",
    "failed",
    "cannot ",
    "does not exist",
    "no valid",
    "is empty",
)

WARNING_KEYWORDS = (
    "skipped",
    "warning",
    "missing",
    "unresolved",
    "manual redesign",
    "manual mapping required",
    "no usable",
    "left undeclared",
    "not relocated",
    "untouched",
    "unable to",
    "not found",
    "no deterministic",
)

# =====================================================================
# Category
# =====================================================================
UNCATEGORISED = "General"
CATEGORY_SEPARATOR = ":"
MAX_CATEGORY_WORDS = 4

# Messages carrying no prefix are grouped here rather than each becoming
# its own single-item category.
FALLBACK_CATEGORY = "Converter"

# =====================================================================
# UI labels - Validation tab
# =====================================================================
UI_VALIDATION_HEADER = "## Validation"
UI_VALIDATION_INTRO = (
    "Errors and warnings need action. Info entries are the conversion "
    "log: each one records a pass that ran normally."
)

UI_METRIC_ERRORS = "Errors"
UI_METRIC_WARNINGS = "Warnings"
UI_METRIC_INFO = "Info"
UI_METRIC_TOTAL = "Total"

UI_CLEAN_RUN = "No errors or warnings. The conversion completed cleanly."
UI_NO_MESSAGES = (
    "No validation messages yet. Generate DB2 COBOL from the Main tab."
)
UI_ERRORS_HEADER = "### Errors"
UI_WARNINGS_HEADER = "### Warnings"
UI_INFO_HEADER = "### Conversion log"
UI_INFO_CAPTION = (
    "{count} entries. Each records a pass that completed normally."
)

UI_FILTER_SEVERITY = "Severity"
UI_FILTER_CATEGORY = "Category"
UI_FILTER_SEARCH = "Search text"
UI_FILTER_SEARCH_PLACEHOLDER = "for example: cursor, counter, date"
UI_NO_MATCH = "No message matches the current filter."

# =====================================================================
# UI labels - Diagnostics tab
# =====================================================================
UI_DIAGNOSTICS_HEADER = "## Diagnostics"
UI_DIAGNOSTICS_INTRO = (
    "What the parsers read from each uploaded file, and what the "
    "converter derived from it."
)

UI_FILES_HEADER = "### Uploaded files"
UI_FILES_EMPTY = "No files loaded. Use Load and Analyze Inputs first."
UI_PARSER_HEADER = "### Parser diagnostics"
UI_PARSER_EMPTY = (
    "No diagnostics available. Click Load and Analyze Inputs first."
)
UI_RAW_HEADER = "Raw log"

COLUMN_ROLE = "Input role"
COLUMN_FILE = "File"
COLUMN_SEVERITY = "Severity"
COLUMN_CATEGORY = "Category"
COLUMN_MESSAGE = "Message"
COLUMN_COUNT = "Entries"

MESSAGE_TABLE_COLUMNS = (
    COLUMN_SEVERITY,
    COLUMN_CATEGORY,
    COLUMN_MESSAGE,
)

# =====================================================================
# Downloads
# =====================================================================
UI_DOWNLOAD_VALIDATION = "Download validation report (csv)"
UI_DOWNLOAD_DIAGNOSTICS = "Download diagnostics (txt)"
UI_FILE_VALIDATION = "validation_report.csv"
UI_FILE_DIAGNOSTICS = "diagnostics.txt"
UI_MIME_CSV = "text/csv"
UI_MIME_TEXT = "text/plain"


WARNING_KEYWORDS = tuple(WARNING_KEYWORDS) + (
    "refused rather than",
    "left for manual review",
    "left unchanged",
    "no readable pic",
    "is not wired into this build",
    "0 movable field",
)