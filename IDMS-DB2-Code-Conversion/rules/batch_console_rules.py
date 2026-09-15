# LOCATION: rules/batch_console_rules.py
# ACTION: CREATE NEW FILE

"""Batch execution console presentation rules.

Constants only. No regex, no runtime logic, no program / record / table
names.

The COBOL team watches this output in a terminal, not in a log file. It
therefore has to be short, aligned, and unambiguous about pass or fail.
Everything it can print is declared here so wording and width are changed
in one place.
"""

from __future__ import annotations

# =====================================================================
# Frame
# =====================================================================
CONSOLE_WIDTH = 80
RULE_HEAVY = "=" * CONSOLE_WIDTH
RULE_LIGHT = "-" * (CONSOLE_WIDTH - 2)
INDENT = "  "

TITLE = "IDMS -> DB2 BATCH EXECUTION"
STARTED_TEMPLATE = "Started {stamp}"
FINISHED_TEMPLATE = "Finished {stamp}"
TIMESTAMP_FORMAT = "%d-%m-%Y %H:%M:%S"

SECTION_INPUTS = "INPUTS"
SECTION_EXECUTION = "EXECUTION"
SECTION_METADATA = "METADATA"
SECTION_SUMMARY = "SUMMARY"
SECTION_ARTEFACTS = "ARTEFACTS"

# =====================================================================
# Progress bar
# =====================================================================
BAR_WIDTH = 20

# Block glyphs read better, but a legacy console code page cannot render
# them. BatchConsole falls back to the ASCII pair automatically.
BAR_FILLED_UNICODE = "\u2588"
BAR_EMPTY_UNICODE = "\u2591"
BAR_FILLED_ASCII = "#"
BAR_EMPTY_ASCII = "-"

BAR_OPEN = "["
BAR_CLOSE = "]"

STEP_LABEL_WIDTH = 24
STEP_COUNTER_TEMPLATE = "[{index}/{total}]"
PULSE_INTERVAL_SECONDS = 0.12
PULSE_SEGMENT = 5

# =====================================================================
# Status
# =====================================================================
STATUS_RUNNING = "RUNNING"
STATUS_OK = "OK"
STATUS_ACCEPTED = "ACCEPTED"
STATUS_REJECTED = "REJECTED"
STATUS_FAILED = "FAILED"
STATUS_SKIPPED = "SKIPPED"
STATUS_NOTHING = "NOTHING"

STATUS_WIDTH = 9

PASSING_STATUSES = (STATUS_OK, STATUS_ACCEPTED, STATUS_SKIPPED, STATUS_NOTHING)
FAILING_STATUSES = (STATUS_REJECTED, STATUS_FAILED)

# Exit code -> status, for the code review runners.
# 0 accepted, 1 rejected, 2 error or nothing to do.
REVIEW_EXIT_STATUS = {
    0: STATUS_ACCEPTED,
    1: STATUS_REJECTED,
    2: STATUS_NOTHING,
}
CONVERT_EXIT_STATUS = {
    0: STATUS_OK,
}

# =====================================================================
# Steps
#
# (key, label, module path, is_review)
# Module paths are relative to the project root and are launched as
# subprocesses, so a change to a runner's internals cannot break this
# orchestrator.
# =====================================================================
STEP_CONVERT_RETRIEVAL = "convert_retrieval"
STEP_CONVERT_UPDATE = "convert_update"
STEP_REVIEW_RETRIEVAL = "review_retrieval"
STEP_REVIEW_UPDATE = "review_update"

STEP_DEFINITIONS = (
    (
        STEP_CONVERT_RETRIEVAL,
        "Convert retrieval",
        "src/idms_db2_phase2/testing/run_retrieval.py",
        False,
    ),
    (
        STEP_CONVERT_UPDATE,
        "Convert update",
        "src/idms_db2_phase2/testing/run_update.py",
        False,
    ),
    (
        STEP_REVIEW_RETRIEVAL,
        "Review retrieval",
        "code_review/runner/review_retrieval.py",
        True,
    ),
    (
        STEP_REVIEW_UPDATE,
        "Review update",
        "code_review/runner/review_update.py",
        True,
    ),
)

MODE_RETRIEVAL = "retrieval"
MODE_UPDATE = "update"
MODE_ALL = "all"
MODES = (MODE_ALL, MODE_RETRIEVAL, MODE_UPDATE)

REVIEW_QUIET_ARG = "--quiet"

# =====================================================================
# Input labels
# =====================================================================
LABEL_WIDTH = 22

LABEL_MAPPING_SHEET = "Mapping Sheet"
LABEL_DCLGEN = "DCLGen"
LABEL_COPYBOOK = "Copybook"
LABEL_RETRIEVAL_PROGRAMS = "Retrieval programs"
LABEL_UPDATE_PROGRAMS = "Update programs"

LABEL_MAPPING_ROWS = "Sheet Mapping rows"
LABEL_DCLGEN_COLUMNS = "DCLGEN columns"
LABEL_COPYBOOK_FIELDS = "Copybook fields"

LABEL_OUTPUT_FOLDER = "Output"
LABEL_REPORT_FOLDER = "Reports"
LABEL_LOG_FOLDER = "Logs"

COUNT_FILE_SINGULAR = "{count} file"
COUNT_FILE_PLURAL = "{count} files"
COUNT_NONE = "none"
VALUE_UNKNOWN = "-"

# =====================================================================
# Summary table
# =====================================================================
SUMMARY_COLUMN_STEP = "Step"
SUMMARY_COLUMN_STATUS = "Status"
SUMMARY_COLUMN_SECONDS = "Seconds"

SUMMARY_HEADER_TEMPLATE = "{step:<28}{status:<12}{seconds:>9}"
SUMMARY_ROW_TEMPLATE = "{step:<28}{status:<12}{seconds:>9}"
SUMMARY_TOTAL_TEMPLATE = "Total {seconds:.1f}s     Failures {failures}"

VERDICT_PASSED = "BATCH COMPLETED - all steps passed"
VERDICT_FAILED_SINGULAR = "BATCH REJECTED - {count} step needs attention"
VERDICT_FAILED_PLURAL = "BATCH REJECTED - {count} steps need attention"

# =====================================================================
# Messages
# =====================================================================
MSG_STEP_SKIPPED = "Skipped by --mode {mode}."
MSG_RUNNER_MISSING = "Runner not found: {path}"
MSG_NO_PROGRAMS = "No programs found for this step."
MSG_DETAIL_HEADER = "Detail for failing steps"
MSG_HINT_REPORTS = (
    "Open the report folder above for the per-criterion breakdown."
)

# Exit codes for the batch itself.
EXIT_OK = 0
EXIT_REJECTED = 1
EXIT_ERROR = 2

# =====================================================================
# Colour
#
# Disabled automatically when stdout is not a terminal, or when NO_COLOR
# is set. Never required for correctness: every status is also a word.
# =====================================================================
ENABLE_COLOUR = True
NO_COLOUR_ENV = "NO_COLOR"

COLOUR_RESET = "\033[0m"
COLOUR_BOLD = "\033[1m"
COLOUR_DIM = "\033[2m"
COLOUR_GREEN = "\033[32m"
COLOUR_RED = "\033[31m"
COLOUR_YELLOW = "\033[33m"
COLOUR_CYAN = "\033[36m"

STATUS_COLOURS = {
    STATUS_OK: COLOUR_GREEN,
    STATUS_ACCEPTED: COLOUR_GREEN,
    STATUS_RUNNING: COLOUR_CYAN,
    STATUS_REJECTED: COLOUR_RED,
    STATUS_FAILED: COLOUR_RED,
    STATUS_SKIPPED: COLOUR_DIM,
    STATUS_NOTHING: COLOUR_YELLOW,
}

# LOCATION: rules/batch_console_rules.py
# ACTION: APPEND at the end of the file

# =====================================================================
# Step execution
# =====================================================================
# A runner that hangs must not hang the batch. Generous, because a large
# program folder legitimately takes minutes.
STEP_TIMEOUT_SECONDS = 900

# Note rendered beside a completed review step.
REVIEW_NOTE_TEMPLATE = "{reviewed} reviewed, {accepted} accepted, {rejected} rejected"

# Fallback when the runner output does not name its report folder.
DEFAULT_REPORT_FOLDER = "code_review/report/output"

# LOCATION: rules/batch_console_rules.py
# ACTION: APPEND at the end of the file

# =====================================================================
# Failure detail
# =====================================================================
# Log levels worth showing in the console. INFO and DEBUG belong in the
# log file, not in a summary a COBOL reviewer reads at a glance.
DETAIL_LOG_LEVELS = ("WARNING", "ERROR", "CRITICAL")

# Hard cap so one broken step cannot flood the terminal.
DETAIL_MAX_LINES = 12

MSG_BLOCKING_TEMPLATE = "Blocking checks: {ids}"
MSG_VERDICT_TEMPLATE = "{verdict} {name}"
MSG_NO_DETAIL = "No error detail reported. See the log folder above."

LABEL_MODE = "Mode"

# LOCATION: rules/batch_console_rules.py
# ACTION: APPEND at the end of the file

# =====================================================================
# Line control
# =====================================================================
# Overwriting an animated line with a shorter one leaves the tail of the
# old line in the terminal buffer. Writing spaces then returning is not
# enough either: the spaces persist until something overwrites them, and
# they end up in any copied transcript. An explicit erase-line is clean.
CARRIAGE_RETURN = "\r"
ERASE_LINE = "\033[2K"
CLEAR_PAD_WIDTH = CONSOLE_WIDTH + 40