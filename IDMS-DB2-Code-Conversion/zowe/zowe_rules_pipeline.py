# LOCATION: zowe/zowe_rules_pipeline.py
# ACTION: CREATE NEW FILE
"""Workspace layout, pipeline steps, runners and console templates.

Constants only.
"""

from __future__ import annotations

# ---- Workspace folders ----
WORKSPACE_SUBFOLDERS = (
    "Mapping Sheet",
    "Program",
    "Copybook",
    "DCLGen",
    "Subschema",
    "Output",
    "Review",
    "Logs",
)

# ---- Steps and commands ----
STEP_FETCH = "fetch"
STEP_CONVERT = "convert"
STEP_REVIEW = "review"
STEP_UPLOAD = "upload"
STEP_ALL = "all"
STEP_SHOW = "show"
STEP_INIT = "init"
STEP_CLEAN = "clean"
STEP_PLAN = "plan"

PIPELINE_STEPS = (STEP_FETCH, STEP_CONVERT, STEP_REVIEW, STEP_UPLOAD)
PIPELINE_COMMANDS = PIPELINE_STEPS + (
    STEP_ALL,
    STEP_SHOW,
    STEP_INIT,
    STEP_CLEAN,
    STEP_PLAN,
)

# ---- Subprocess runners ----
CONVERT_RUNNER = "src/idms_db2_phase2/testing/run_retrieval.py"
REVIEW_RUNNER = "code_review/runner/review_file.py"
REVIEW_KIND = "UNKNOWN"

IDMS_INPUT_DIR_KEY = "IDMS_INPUT_DIR"
PYTHONPATH_KEY = "PYTHONPATH"
PYTHONPATH_ENTRIES = ("src", ".")
UNBUFFERED_KEY = "PYTHONUNBUFFERED"
STEP_TIMEOUT_SECONDS = 1800

# ---- Statuses and exit codes ----
STATUS_OK = "OK"
STATUS_FAILED = "FAILED"
STATUS_SKIPPED = "SKIPPED"
STATUS_NOTHING = "NOTHING"

EXIT_OK = 0
EXIT_NOTHING = 1
EXIT_ERROR = 2

# ---- Console templates ----
PIPELINE_TITLE = "Zowe Pipeline"
STEP_HEADER_TEMPLATE = "STEP {index}/{total}  {step}"
STEP_OK_TEMPLATE = "{step} completed in {seconds:.1f}s"
STEP_FAILED_TEMPLATE = "{step} FAILED (exit {code}) after {seconds:.1f}s"
STEP_SKIPPED_TEMPLATE = "{step} skipped. Reason: {reason}"
STEP_NOTHING_TEMPLATE = "{step} had nothing to do."
SUMMARY_HEADER = "Step       Status        Seconds"
SUMMARY_ROW_TEMPLATE = "{step:<10} {status:<12} {seconds:>8.1f}s"
VERDICT_OK = "PIPELINE COMPLETED - every step passed"
VERDICT_FAILED_TEMPLATE = "PIPELINE STOPPED - {step} failed"
WORKSPACE_CREATED_TEMPLATE = "Created workspace folder: {folder}"
WORKSPACE_READY_TEMPLATE = "Workspace ready: {folder}"
CLEAN_REMOVED_TEMPLATE = "Cleaned: {folder}"
MAPPING_MISSING_TEMPLATE = (
    "No mapping sheet found in {folder}. Place the Excel or CSV file there "
    "before running convert."
)
RUNNER_MISSING_TEMPLATE = "Runner not found: {path}"