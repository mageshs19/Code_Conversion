# LOCATION: src/idms_db2_phase2/composers/update_sql_cleanup/update_sql_cleanup_patterns.py
# ACTION: REPLACE ENTIRE FILE

"""
Update-program SQL cleanup regex patterns.

Regex belongs here, not inside the shared base class.
"""

import re

CONVERTED_OBTAIN_CALC_PATTERN = re.compile(
    r"^\s*\*?\s*DB2:\s*Converted\s+OBTAIN\s+CALC\s+for\s+(?P<record>[A-Z0-9-]+)\.?\s*$",
    flags=re.IGNORECASE,
)

CONVERTED_MODIFY_PATTERN = re.compile(
    r"^\s*\*?\s*DB2:\s*Converted\s+MODIFY\s+for\s+(?P<record>[A-Z0-9-]+)\.?\s*$",
    flags=re.IGNORECASE,
)

EXEC_SQL_START_PATTERN = re.compile(
    r"^\s*EXEC\s+SQL\b",
    flags=re.IGNORECASE,
)

EXEC_SQL_END_PATTERN = re.compile(
    r"^\s*END-EXEC\.?\s*$",
    flags=re.IGNORECASE,
)

INCLUDE_PATTERN = re.compile(
    r"^\s*INCLUDE\s+(?P<include>[A-Z0-9]+)\b",
    flags=re.IGNORECASE,
)

SQLCODE_IF_PATTERN = re.compile(
    r"^\s*IF\s+SQLCODE\b",
    flags=re.IGNORECASE,
)

END_IF_PATTERN = re.compile(
    r"^\s*END-IF\.?\s*$",
    flags=re.IGNORECASE,
)

MALFORMED_SQLERROR_ENDIF_PATTERN = re.compile(
    r"^(?P<indent>\s*)PERFORM\s+SQLERROR\.?END-IF\.?\s*$",
    flags=re.IGNORECASE,
)

MOVE_TO_BARE_FIELD_PATTERN = re.compile(
    r"^\s*MOVE\s+(?P<src>.+?)\s+TO\s+(?P<tgt>[A-Z][A-Z0-9-]+)\.?\s*$",
    flags=re.IGNORECASE,
)

MOVE_TO_DCL_HOST_PATTERN = re.compile(
    r"^\s*MOVE\s+(?P<src>.+?)\s+TO\s+(?P<host>[A-Z][A-Z0-9-]+)\s+OF\s+(?P<group>DCL[A-Z0-9-]+)\.?\s*$",
    flags=re.IGNORECASE,
)

SQL_LOCATION_PATTERN = re.compile(
    r"^\s*01\s+SQL-LOCATION\b",
    flags=re.IGNORECASE,
)

LINKAGE_SECTION_PATTERN = re.compile(
    r"^\s*LINKAGE\s+SECTION\.",
    flags=re.IGNORECASE,
)

TIMESTAMP_PARAGRAPH_PATTERN = re.compile(
    r"^\s*600-GET-TIMESTAMP\.\s*$",
    flags=re.IGNORECASE,
)

STOP_RUN_PATTERN = re.compile(
    r"^\s*STOP\s+RUN\.?\s*$",
    flags=re.IGNORECASE,
)

# --- SQLCODE handling block detection (IF and EVALUATE forms) ---

SQLCODE_EVALUATE_PATTERN = re.compile(
    r"^\s*EVALUATE\s+SQLCODE\b",
    flags=re.IGNORECASE,
)

END_EVALUATE_PATTERN = re.compile(
    r"^\s*END-EVALUATE\.?\s*$",
    flags=re.IGNORECASE,
)

# A lone period line that closes an EVALUATE block (COBOL scope terminator).
LONE_PERIOD_PATTERN = re.compile(
    r"^\s*\.\s*$",
    flags=re.IGNORECASE,
)