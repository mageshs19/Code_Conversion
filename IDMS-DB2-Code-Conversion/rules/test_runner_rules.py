# LOCATION: rules/test_runner_rules.py
# ACTION: CREATE NEW FILE

"""Test runner rules.

Constants only. No regex, no runtime logic, no program / record / table
names.

The runner shells out to pytest and reads its JUnit XML report. JUnit XML
is built into pytest core, so no extra plugin is added to the project.
"""

from __future__ import annotations

# =====================================================================
# Discovery
# =====================================================================
TESTS_FOLDER = "tests"
TEST_FILE_GLOB = "test_*.py"
ALL_TESTS_LABEL = "All tests"

# =====================================================================
# Invocation
# =====================================================================
PYTEST_MODULE = "pytest"
PYTEST_BASE_ARGS = (
    "-q",
    "--tb=short",
    "--no-header",
    "-p", "no:cacheprovider",
)
JUNIT_ARG_TEMPLATE = "--junit-xml={path}"
KEYWORD_ARG = "-k"
VERBOSE_ARG = "-vv"

# Seconds before the run is abandoned. A converter test suite that hangs
# is a defect in its own right; the UI must not hang with it.
RUN_TIMEOUT_SECONDS = 600

# PYTHONPATH handed to the subprocess. Both entries are required: the
# converter lives under src/, while rules/, patterns/ and catalogs/ sit
# at the project root.
PYTHONPATH_ENTRIES = ("src", ".")
PYTHONPATH_SEPARATOR_KEY = "PYTHONPATH"

# =====================================================================
# Outcomes
# =====================================================================
OUTCOME_PASSED = "PASSED"
OUTCOME_FAILED = "FAILED"
OUTCOME_ERROR = "ERROR"
OUTCOME_SKIPPED = "SKIPPED"

FAILING_OUTCOMES = (OUTCOME_FAILED, OUTCOME_ERROR)

OUTCOME_ICONS = {
    OUTCOME_PASSED: "PASS",
    OUTCOME_FAILED: "FAIL",
    OUTCOME_ERROR: "ERROR",
    OUTCOME_SKIPPED: "SKIP",
}

# =====================================================================
# UI labels
# =====================================================================
UI_TAB_TITLE = "Tests"
UI_HEADER = "## Python Test Suite"
UI_INTRO = (
    "Run the converter's pytest suite and review the outcome per test. "
    "Results stay on screen until the next run."
)
UI_RUN_BUTTON = "Run Tests"
UI_RUNNING = "Running pytest..."
UI_TARGET_LABEL = "Test target"
UI_KEYWORD_LABEL = "Filter by keyword (pytest -k)"
UI_KEYWORD_PLACEHOLDER = "for example: reflow or counter"
UI_VERBOSE_LABEL = "Verbose output"
UI_FAILURES_ONLY_LABEL = "Show failures only"

UI_METRIC_TOTAL = "Total"
UI_METRIC_PASSED = "Passed"
UI_METRIC_FAILED = "Failed"
UI_METRIC_SKIPPED = "Skipped"
UI_METRIC_DURATION = "Duration (s)"

UI_TABLE_HEADER = "### Results"
UI_DETAIL_HEADER = "### Failure detail"
UI_OUTPUT_HEADER = "### Raw pytest output"
UI_COMMAND_HEADER = "### Command"

UI_NO_RESULT = (
    "No test run yet. Press Run Tests to execute the suite."
)
UI_NO_TESTS_FOUND = (
    "No test files found in the tests folder."
)
UI_ALL_PASSED = "All tests passed."
UI_SOME_FAILED = "{failed} test(s) failed."
UI_TIMED_OUT = (
    "The test run exceeded {seconds} seconds and was stopped."
)
UI_RUN_ERROR = "The test run could not be started: {reason}"

UI_DOWNLOAD_CSV = "Download results (csv)"
UI_DOWNLOAD_LOG = "Download raw output (txt)"
UI_FILE_CSV = "test_results_{stamp}.csv"
UI_FILE_LOG = "test_output_{stamp}.txt"
UI_MIME_CSV = "text/csv"
UI_MIME_TEXT = "text/plain"

TIMESTAMP_FORMAT = "%d-%m-%Y %H:%M:%S"
FILE_TIMESTAMP_FORMAT = "%d-%m-%Y_%H%M%S"

# =====================================================================
# Table columns
# =====================================================================
COLUMN_OUTCOME = "Outcome"
COLUMN_MODULE = "Module"
COLUMN_TEST = "Test"
COLUMN_DURATION = "Seconds"
COLUMN_MESSAGE = "Message"

TABLE_COLUMNS = (
    COLUMN_OUTCOME,
    COLUMN_MODULE,
    COLUMN_TEST,
    COLUMN_DURATION,
    COLUMN_MESSAGE,
)

MESSAGE_PREVIEW_LENGTH = 160