"""Display text only.

No logic, no regex, no paths, no program names. Every string the code
review prints, writes or renders is declared here so wording stays in one
place and the COBOL team can reword the report without touching logic.
"""

from __future__ import annotations

# ---- Outcome symbols -------------------------------------------------
SYMBOL = {
    "PASS": "PASS ",
    "FAIL": "FAIL ",
    "SKIPPED": "SKIP ",
    "BLOCKED": "BLOCK",
}

# ---- Placeholders ----------------------------------------------------
VALUE_UNNAMED = "(unnamed)"
VALUE_UNKNOWN = "(unknown)"
VALUE_IN_MEMORY = "(in memory)"

# ---- Report header ---------------------------------------------------
REPORT_TITLE = "Code Review Report"
RULE = "-" * 74

F_PROGRAM = "Program            : {value}"
F_KIND = "Program Kind       : {value}"
F_SOURCE = "Reviewed File      : {value}"
F_WHEN = "Reviewed           : {value}"
F_TOTALS = (
    "Checks             : {passed} passed, {failed} failed, "
    "{skipped} skipped, {blocked} blocked"
)
F_CRITERIA = (
    "Criteria           : {passed} passed, {failed} failed, "
    "{skipped} skipped, {blocked} blocked"
)
F_RESULT = "Result             : {value}"
F_BLOCKING = "Blocking           : {value}"

ACCEPTED = "ACCEPTED"
REJECTED = "REJECTED"

# ---- Report body -----------------------------------------------------
H_DETAIL = "Detail"
H_FAILURES = "Failures"
NO_FAILURES = "No failures."

F_CHECK = "{symbol} {check_id} {severity:<8} {title}"
F_CRIT = "        {criterion_id} {description}"
F_FIND = "            {finding}"
F_NOTE = "            note : {note}"

F_FAIL_CHECK = "{check_id}  {severity:<8}  {title}"
F_FAIL_CRIT = "    {criterion_id}  {description}"
F_FAIL_NOTE = "        {note}"

# ---- CSV -------------------------------------------------------------
CSV_HEADER = (
    "Program", "Reviewed", "File", "Check", "Severity", "Title",
    "Criterion", "Description", "Outcome", "Note", "Lines",
)
CSV_SUMMARY_HEADER = (
    "Program", "Kind", "Reviewed", "File",
    "Passed", "Failed", "Skipped", "Blocked", "Result",
)
CSV_TIMESTAMP_FORMAT = "%d-%m-%Y %H:%M:%S"
CSV_LINE_SEPARATOR = " "

# ---- Streamlit panel -------------------------------------------------
UI_TITLE = "Code Review"
UI_NOT_READY = "Generate DB2 COBOL first, then run the code review."
UI_RUN = "Run Code Review"
UI_RUN_HINT = "Click Run Code Review to score the generated program."
UI_ACCEPTED = "Accepted. No blocking failures."
UI_REJECTED = "Rejected. Blocking checks: {ids}"
UI_UNAVAILABLE = "Code review unavailable: {reason}"

UI_TARGET = "Ready to review `{file}` as a **{kind}** program."
UI_STALE = (
    "The generated program changed since this report was produced. "
    "The stale report was discarded. Run the code review again."
)
UI_SCOPE = (
    "This panel reviews the program currently in the session, not files "
    "on disk. Use review_file.py to review a specific .cbl."
)

UI_PROGRAM = "Program **{name}**  |  Kind **{kind}**  |  File `{file}`"
UI_METRIC_PASSED = "Checks passed"
UI_METRIC_FAILED = "Checks failed"
UI_METRIC_SKIPPED = "Checks skipped"
UI_METRIC_BLOCKED = "Checks blocked"
UI_CRITERIA = (
    "Criteria: {passed} passed, {failed} failed, "
    "{skipped} skipped, {blocked} blocked"
)

UI_FILTER_FAILURES = "Show failures only"
UI_FILTER_SKIPS = "Show skip reasons"
UI_CHECK_LABEL = "{outcome}  |  {check_id}  |  {severity}  |  {title}"
UI_CRITERION = "`{mark}` **{criterion_id}** {description}"
UI_MARK_PASS = "OK  "

UI_DOWNLOAD_TEXT = "Download report (text)"
UI_DOWNLOAD_CSV = "Download report (csv)"
UI_FILE_TEXT = "{stem}_code_review.txt"
UI_FILE_CSV = "{stem}_code_review.csv"
UI_MIME_TEXT = "text/plain"
UI_MIME_CSV = "text/csv"
UI_DEFAULT_STEM = "review"

# ---- Runner banners --------------------------------------------------
H_RUN_FILE = "Code Review"
H_RUN_RETRIEVAL = "Retrieval Code Review"
H_RUN_UPDATE = "Update Code Review"

MSG_REVIEWED_FOLDER = "Reviewed Folder    : {folder}"
MSG_PROGRAM_FOLDER = "Program Folder     : {folder}"
MSG_PROGRAM_COUNT = "Program Count      : {count}"
MSG_OUTPUT_FOLDER = "Output Folder      : {folder}"
MSG_REPORT_FOLDER = "Report Folder      : {folder}"
MSG_FILE_COUNT = "Files              : {count}"
MSG_PROGRAM_KIND = "Program Kind       : {kind}"

# ---- Runner summary --------------------------------------------------
MSG_SUMMARY = "Reviewed : {reviewed}   Accepted : {accepted}   Rejected : {rejected}"
MSG_CONVERSION_FAILED = "Conversion failed  : {names}"
MSG_REPORTS_WRITTEN = "Reports written to : {folder}"
MSG_QUIET_LINE = "{verdict:<9} {name}{suffix}"
MSG_QUIET_BLOCKING = " blocking: {ids}"

# ---- Runner errors ---------------------------------------------------
MSG_ERROR = "ERROR: {message}"
MSG_FILE_NOT_FOUND = "File not found: {path}"
MSG_FOLDER_NOT_FOUND = "Folder not found: {folder}"
MSG_PATH_NOT_FOLDER = "Path is not a folder: {folder}"
MSG_SOURCE_NOT_FOUND = "Source file not found: {path}"
MSG_CONVERSION_ERROR = "Conversion failed for {name}: {reason}"

# ---- Nothing generated yet -------------------------------------------
MSG_NO_OUTPUT_TITLE = "Nothing to review."
MSG_NO_OUTPUT_FOUND = (
    "No .cbl files found in: {folder}\n"
    "The folder exists but is empty, so no DB2 COBOL has been generated yet."
)
MSG_NO_OUTPUT_HINT = (
    "Next step: run the conversion first, then run the code review again.\n"
    "  set PYTHONPATH=src\n"
    "  python code_review\\runner\\review_retrieval.py   (retrieval programs)\n"
    "  python code_review\\runner\\review_update.py      (update programs)"
)

# ---- Nothing to convert ----------------------------------------------
MSG_NO_PROGRAMS_TITLE = "Nothing to convert."
MSG_NO_PROGRAMS_FOUND = (
    "No {kind} programs found in: {folder}\n"
    "The folder exists but holds no program file to convert."
)
MSG_NO_PROGRAMS_HINT = (
    "Next step: place at least one .txt, .cbl or .cob program in that\n"
    "folder, then run this command again."
)

KIND_LABEL_RETRIEVAL = "retrieval"
KIND_LABEL_UPDATE = "update"