from __future__ import annotations

import re

# Regex patterns for final update-only COBOL cleanup.
#
# Regex only.
# No business rules, conversion rules, file paths, program names, DB2 table
# names, DCLGEN names, copybook names, or host variables.

CONVERTED_MODIFY_COMMENT_PATTERN = re.compile(
    r"DB2:\s*Converted\s+MODIFY\s+for\s+[A-Z0-9-]+\.?",
    flags=re.IGNORECASE,
)

UPDATE_PARAGRAPH_PATTERN = re.compile(
    r"^1100-UPDATE-[A-Z0-9-]+\.$",
    flags=re.IGNORECASE,
)

PARAGRAPH_HEADER_PATTERN = re.compile(
    r"^[A-Z0-9][A-Z0-9-]*\.$",
    flags=re.IGNORECASE,
)

EXEC_SQL_PATTERN = re.compile(
    r"^EXEC\s+SQL\b",
    flags=re.IGNORECASE,
)

END_EXEC_PATTERN = re.compile(
    r"^END-EXEC\.?$",
    flags=re.IGNORECASE,
)

EVALUATE_SQLCODE_PATTERN = re.compile(
    r"^EVALUATE\s+SQLCODE\b",
    flags=re.IGNORECASE,
)

END_EVALUATE_PATTERN = re.compile(
    r"^END-EVALUATE\.?$",
    flags=re.IGNORECASE,
)

WHEN_PATTERN = re.compile(
    r"^WHEN\b",
    flags=re.IGNORECASE,
)

PROCESS_COMMIT_IF_PATTERN = re.compile(
    r"^IF\s+[A-Z0-9-]+\s*>\s*[0-9]+\.?$",
    flags=re.IGNORECASE,
)

PERFORM_PATTERN = re.compile(
    r"^PERFORM\b",
    flags=re.IGNORECASE,
)

STOP_RUN_PATTERN = re.compile(
    r"^STOP\s+RUN\.?$",
    flags=re.IGNORECASE,
)

# Existing non-SQL DCLGROUP.FIELD detector (preserved, backward-compatible).
NON_SQL_DCL_DOT_REFERENCE_PATTERN = re.compile(
    r"(?<!:)\b(?P<group>DCL[A-Z0-9-]+)\.(?P<field>[A-Z][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)

MOVE_SPACES_TO_BARE_RECORD_PATTERN = re.compile(
    r"^MOVE\s+SPACES?\s+TO\s+(?P<record>[A-Z][A-Z0-9-]*)\.?$",
    flags=re.IGNORECASE,
)

INITIALIZE_DCL_PATTERN = re.compile(
    r"^INITIALIZE\s+(?P<group>DCL[A-Z0-9-]+)\.?",
    flags=re.IGNORECASE,
)

DCL_REFERENCE_PATTERN = re.compile(
    r"\bDCL[A-Z0-9-]+\b",
    flags=re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# ADDED: robust generic handling for non-SQL "MOVE ... TO DCLGROUP.FIELD".
#
# These patterns fix the remaining case where a non-SQL COBOL MOVE still uses
# DCLGEN dot notation (DCLGROUP.FIELD) instead of COBOL "FIELD OF DCLGROUP".
# They deliberately do NOT require a trailing \b, so long DCLGEN host names
# with embedded digit-runs (e.g. DA-INFSDGD-479BFAR) are captured in full.
# SQL host variables (":DCLGROUP.FIELD") are never matched by these because
# the cleanup pass skips lines inside EXEC SQL ... END-EXEC blocks.
# ---------------------------------------------------------------------------

# One-line: MOVE <source> TO DCLGROUP.FIELD
MOVE_TO_DCL_DOT_REFERENCE_PATTERN = re.compile(
    r"^MOVE\s+(?P<source>.+?)\s+TO\s+"
    r"(?P<group>DCL[A-Z0-9]+)\.(?P<field>[A-Z][A-Z0-9-]*)\.?$",
    flags=re.IGNORECASE,
)

# Wrapped continuation line: TO DCLGROUP.FIELD
# (the MOVE verb was emitted on the previous physical line by fixed-format
# wrapping).
TO_DCL_DOT_REFERENCE_PATTERN = re.compile(
    r"^TO\s+(?P<group>DCL[A-Z0-9]+)\.(?P<field>[A-Z][A-Z0-9-]*)\.?$",
    flags=re.IGNORECASE,
)

# Hardened in-line fallback detector (no trailing \b) for any remaining
# non-SQL DCLGROUP.FIELD occurrence.
NON_SQL_DCL_DOT_REFERENCE_STRICT_PATTERN = re.compile(
    r"(?<!:)\b(?P<group>DCL[A-Z0-9]+)\.(?P<field>[A-Z][A-Z0-9-]*)",
    flags=re.IGNORECASE,
)