# LOCATION: src/idms_db2_phase2/composers/update_sql_cleanup/composer_patterns.py
# ACTION: CREATE NEW FILE

"""
Regex patterns used only by the update SQL cleanup composer passes.

(The shared base patterns live in update_sql_cleanup_patterns.py.)
"""

import re

MOVE_TO_DCL_DOT_HOST_PATTERN = re.compile(
    r"^\s*MOVE\s+(?P<src>.+?)\s+TO\s+(?P<group>DCL[A-Z0-9-]+)\.(?P<host>[A-Z][A-Z0-9-]+)\.?\s*$",
    flags=re.IGNORECASE,
)

STRING_INTO_DCL_HOST_PATTERN = re.compile(
    r"^\s*INTO\s+(?P<host>[A-Z][A-Z0-9-]+)\s+OF\s+(?P<group>DCL[A-Z0-9-]+)\.?\s*$",
    flags=re.IGNORECASE,
)

STRING_INTO_DCL_DOT_HOST_PATTERN = re.compile(
    r"^\s*INTO\s+(?P<group>DCL[A-Z0-9-]+)\.(?P<host>[A-Z][A-Z0-9-]+)\.?\s*$",
    flags=re.IGNORECASE,
)

ANY_DCL_OF_REFERENCE_PATTERN = re.compile(
    r"\b(?P<host>[A-Z][A-Z0-9-]+)\s+OF\s+(?P<group>DCL[A-Z0-9-]+)\b",
    flags=re.IGNORECASE,
)

ANY_DCL_DOT_REFERENCE_PATTERN = re.compile(
    r"\b(?P<group>DCL[A-Z0-9-]+)\.(?P<host>[A-Z][A-Z0-9-]+)\b",
    flags=re.IGNORECASE,
)

DATE_COLUMN_PREFIXES = (
    "DA_",
    "DT_",
)