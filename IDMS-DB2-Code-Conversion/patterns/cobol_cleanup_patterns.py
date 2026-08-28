"""
COBOL cleanup regex patterns.

Regex patterns belong in patterns/, not in composer classes. These patterns
are shared by the COBOL post-conversion cleanup helper classes.
"""

import re

EXEC_SQL_INCLUDE_PATTERN = re.compile(
    r"\bINCLUDE\s+(?P<include>[A-Z0-9]+)\b",
    flags=re.IGNORECASE,
)

DCL_GROUP_PATTERN = re.compile(
    r"\bDCL(?P<table>[A-Z0-9]+)\b",
    flags=re.IGNORECASE,
)

WORKING_STORAGE_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?WORKING-STORAGE\s+SECTION\.",
    flags=re.IGNORECASE,
)

LINKAGE_SECTION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?LINKAGE\s+SECTION\.",
    flags=re.IGNORECASE,
)

ERROR_STATUS_MOVE_PATTERN = re.compile(
    r"^\s*MOVE\s+['\"]?[A-Z0-9]+['\"]?\s+TO\s+ERROR-STATUS\.?\s*$",
    flags=re.IGNORECASE,
)

WS_STATUS_PATTERN = re.compile(
    r"^\s*10\s+WS-STATUS\b",
    flags=re.IGNORECASE,
)

SW_STATUS_D_PIC_PATTERN = re.compile(
    r"\bSW-STATUS-D\b.+\bPIC\b",
    flags=re.IGNORECASE,
)

SW_STATUS_D_MOVE_N_PATTERN = re.compile(
    r"^\s*MOVE\s+['\"]N['\"]\s+TO\s+SW-STATUS-D\.?\s*$",
    flags=re.IGNORECASE,
)

FETCH_UNTIL_EOC_PATTERN = re.compile(
    r"^(?P<prefix>\s*PERFORM\s+)"
    r"(?P<fetch>[0-9]+-FETCH-[A-Z0-9-]+)"
    r"\s+UNTIL\s+(?P<eoc>[A-Z0-9-]+-EOC)\.?\s*$",
    flags=re.IGNORECASE,
)

FETCH_UNTIL_EOC_OR_SW_PATTERN = re.compile(
    r"^(?P<prefix>\s*PERFORM\s+)"
    r"(?P<fetch>[0-9]+-FETCH-[A-Z0-9-]+)"
    r"\s+UNTIL\s+(?P<eoc>[A-Z0-9-]+-EOC)\s+OR\s+SW-STATUS-D\s*$",
    flags=re.IGNORECASE,
)

FETCH_UNTIL_EOC_FULL_SW_PATTERN = re.compile(
    r"^(?P<prefix>\s*PERFORM\s+)"
    r"(?P<fetch>[0-9]+-FETCH-[A-Z0-9-]+)"
    r"\s+UNTIL\s+(?P<eoc>[A-Z0-9-]+-EOC)"
    r"\s+OR\s+SW-STATUS-D\s*=?\s*['\"]?Y['\"]?\.?\s*$",
    flags=re.IGNORECASE,
)

SW_STATUS_Y_CONTINUATION_PATTERN = re.compile(
    r"^\s*=?\s*['\"]?Y['\"]?\.?\s*$",
    flags=re.IGNORECASE,
)

WRITE_PATTERN = re.compile(
    r"^\s*WRITE\s+(?P<record>[A-Z0-9-]+)\.?\s*$",
    flags=re.IGNORECASE,
)

INITIALIZE_PATTERN = re.compile(
    r"^\s*INITIALIZE\s+(?P<record>[A-Z0-9-]+)\.?\s*$",
    flags=re.IGNORECASE,
)

MOVE_START_PATTERN = re.compile(
    r"^\s*MOVE\b",
    flags=re.IGNORECASE,
)

MOVE_TO_OUTPUT_FIELD_PATTERN = re.compile(
    r"^\s*MOVE\b.+\bTO\s+(?P<target>UIT-[A-Z0-9-]+)\.?\s*$",
    flags=re.IGNORECASE,
)

TO_OUTPUT_FIELD_PATTERN = re.compile(
    r"^\s*TO\s+(?P<target>UIT-[A-Z0-9-]+)\.?\s*$",
    flags=re.IGNORECASE,
)

DB2_DATE_MOVE_START_PATTERN = re.compile(
    r"^\s*MOVE\s+(?P<field>(?:DA|DT)-[A-Z0-9-]+)\s+OF\s+"
    r"(?P<group>DCL[A-Z0-9-]+)\s*$",
    flags=re.IGNORECASE,
)

DB2_DATE_MOVE_ONE_LINE_PATTERN = re.compile(
    r"^\s*MOVE\s+(?P<field>(?:DA|DT)-[A-Z0-9-]+)\s+OF\s+"
    r"(?P<group>DCL[A-Z0-9-]+)\s+TO\s+"
    r"(?P<target>(?:UIT|OUT)-(?:DA|DT)-[A-Z0-9-]+)\.?\s*$",
    flags=re.IGNORECASE,
)

TO_UIT_DATE_FIELD_PATTERN = re.compile(
    r"^\s*TO\s+(?P<target>(?:UIT|OUT)-(?:DA|DT)-[A-Z0-9-]+)\.?\s*$",
    flags=re.IGNORECASE,
)

FETCH_PARAGRAPH_NUMBER_PATTERN = re.compile(
    r"^(?P<number>\d+)-FETCH-",
    flags=re.IGNORECASE,
)

# LOCATION: patterns/cobol_cleanup_patterns.py
# ACTION: APPEND these patterns to the existing file (add at the end)

import re  # already imported at top; keep single import

# --- Category G: residual IDMS comment-noise cleanup ---

# Generated advisory comments left by the transformer when removing IDMS code.
RESIDUAL_IDMS_COMMENT_PATTERN = re.compile(
    r"^\s*\*\s*DB2:\s*("
    r"Removed\s+residual\s+IDMS\b"
    r"|Removed\s+IDMS\b"
    r"|Removed\s+orphan\s+IDMS\b"
    r"|IDMS\s+record\s+[A-Z0-9-]+\s+was\s+not\s+converted"
    r"|Missing\s+Sheet\s+Mapping\s+and\s+DCLGEN\s+metadata"
    r"|Restart/control\s+logic\s+requires\s+manual\s+DB2\s+redesign"
    r"|IDMS\s+FINISH\s+converted\s+to\s+COMMIT"
    r")",
    flags=re.IGNORECASE,
)

# Continuation of a wrapped comment line (a comment line that is NOT a new
# DB2: marker and NOT a business comment separator like *---- or *****).
RESIDUAL_IDMS_COMMENT_CONTINUATION_PATTERN = re.compile(
    r"^\s*\*\s*(?!DB2:)(?![-*])\S",
    flags=re.IGNORECASE,
)

# A lone CONTINUE. statement.
LONE_CONTINUE_PATTERN = re.compile(
    r"^\s*CONTINUE\.?\s*$",
    flags=re.IGNORECASE,
)

# Block-control keywords whose branch must not be left empty.
BLOCK_OPENER_PATTERN = re.compile(
    r"^\s*(IF|ELSE|WHEN|EVALUATE)\b",
    flags=re.IGNORECASE,
)

# LOCATION: patterns/cobol_cleanup_patterns.py
# ACTION: APPEND this pattern (add near the other Category G patterns)

# Generated OBTAIN CALC removal marker (comment pair emitted before a direct
# UPDATE). Manual standard removes these since the MOVEs flow into the UPDATE.
REMOVED_OBTAIN_CALC_COMMENT_PATTERN = re.compile(
    r"^\s*\*\s*DB2:\s*("
    r"Removed\s+OBTAIN\s+CALC\s+SELECT\s+for\b"
    r"|Direct\s+UPDATE\s+will\s+use\s+mapped\s+composite\s+key"
    r")",
    flags=re.IGNORECASE,
)

# LOCATION: patterns/cobol_cleanup_patterns.py
# ACTION: REPLACE these two patterns

# Generated advisory comments left by the transformer when removing IDMS code.
# NOTE: matches only "* DB2:" (colon after DB2). "*DB2-KEEP:" is deliberately
# NOT matched, so Option B keep-and-comment markers survive cleanup.
RESIDUAL_IDMS_COMMENT_PATTERN = re.compile(
    r"^\s*\*\s*DB2:\s*("
    r"Removed\s+residual\s+IDMS\b"
    r"|Removed\s+IDMS\b"
    r"|Removed\s+orphan\s+IDMS\b"
    r"|IDMS\s+record\s+[A-Z0-9-]+\s+was\s+not\s+converted"
    r"|Missing\s+Sheet\s+Mapping\s+and\s+DCLGEN\s+metadata"
    r"|Restart/control\s+logic\s+requires\s+manual\s+DB2\s+redesign"
    r"|IDMS\s+FINISH\s+converted\s+to\s+COMMIT"
    r")",
    flags=re.IGNORECASE,
)

# Continuation of a wrapped residual comment. Must NOT match:
#   - a new DB2: marker
#   - a DB2-KEEP marker or a kept commented IDMS verb (Option B)
#   - a business separator (*---- or *****)
RESIDUAL_IDMS_COMMENT_CONTINUATION_PATTERN = re.compile(
    r"^\s*\*\s*(?!DB2:)(?!DB2-KEEP)(?![-*])\S",
    flags=re.IGNORECASE,
)