# LOCATION: rules/retrieval_commit_cleanup_rules.py
# ACTION: CREATE NEW FILE
"""Retrieval COMMIT cleanup rules.

Constants only. No regex, no runtime logic, no program / record / table /
cursor / host variable names.

WHY THIS EXISTS

ControlStatementConverter is the ONLY place that should turn FINISH into
COMMIT, and it now honours EMIT_COMMIT_IN_RETRIEVAL. This cleanup is a
SAFETY NET for a COMMIT that reaches the output by any other route - a
COMMIT already present in the legacy source, or one emitted by a future
generator that does not read the flag.

It removes a COMMIT only when the program is RETRIEVAL. It never touches
an update program.
"""

from __future__ import annotations

ENFORCE_RETRIEVAL_COMMIT_CLEANUP = True

# Tokens that identify the generated COMMIT block.
COMMIT_SQL_TOKEN = "COMMIT"
COMMIT_LOCATION_TOKEN = "TO SQL-LOCATION"
EXEC_SQL_TOKEN = "EXEC SQL"
END_EXEC_TOKEN = "END-EXEC"

# Maximum lines scanned forward from EXEC SQL when matching END-EXEC.
BLOCK_SCAN_LIMIT = 8

# Replacement left in place of a removed block, so the reader sees the
# decision instead of a silent deletion.
COMMIT_REMOVED_COMMENT = (
    "* DB2: COMMIT removed; retrieval program is read-only."
)

RETRIEVAL_COMMIT_MESSAGES = {
    "removed": (
        "Retrieval cleanup: removed {count} COMMIT block(s); the program "
        "is read-only."
    ),
    "kept_update": (
        "Retrieval cleanup: program is an update program; COMMIT kept."
    ),
    "none_found": (
        "Retrieval cleanup: no COMMIT block found."
    ),
}
ENFORCE_PARAGRAPH_NOT_EMPTIED = True

CONTINUE_STATEMENT = "CONTINUE."

# How far ahead to look for the next executable statement before
# concluding the paragraph is empty.
EMPTINESS_SCAN_LIMIT = 40

CURSOR_ORDER_CLEANUP_UNUSED = None  # placeholder, keeps imports stable

RETRIEVAL_COMMIT_MESSAGES["continue_added"] = (
    "Retrieval cleanup: added CONTINUE. after the removed COMMIT; it was "
    "the only statement in its paragraph."
)

ENFORCE_PARAGRAPH_NOT_EMPTIED = True

CONTINUE_STATEMENT = "CONTINUE."

# Body geometry for the generated CONTINUE line, measured from column 7.
# One indicator space then four body spaces puts CONTINUE. at column 12,
# which is where CHK-06.07 expects an Area B statement.
CONTINUE_INDICATOR = " "
CONTINUE_INDENT = "    "

# How far ahead to look for the next executable statement before
# concluding the paragraph has been emptied. A paragraph longer than
# this means the boundary test has lost sync, so the guard stands down
# rather than injecting a CONTINUE that may not belong.
EMPTINESS_SCAN_LIMIT = 40

# Single words ending in a period that are NOT paragraph headers.
# Declared here so this pass has no cross-rules dependency.
NON_PARAGRAPH_SINGLE_WORDS = frozenset(
    {
        "CONTINUE",
        "END-EVALUATE",
        "END-EXEC",
        "END-IF",
        "END-PERFORM",
        "END-READ",
        "END-SEARCH",
        "END-STRING",
        "END-WRITE",
        "EXIT",
        "GOBACK",
        "STOP",
    }
)

RETRIEVAL_COMMIT_MESSAGES["continue_added"] = (
    "Retrieval cleanup: added CONTINUE. after the removed COMMIT; it was "
    "the only statement in its paragraph."
)