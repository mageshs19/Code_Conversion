from __future__ import annotations

import re

# Regex patterns for DB2 DATE-host raw-move detection.
#
# Regex only. No business rules, program names, record names, DB2 tables,
# DCLGEN names, copybook names, or host variables.

EXEC_SQL_START_PATTERN = re.compile(
    r"^EXEC\s+SQL\b",
    flags=re.IGNORECASE,
)

END_EXEC_PATTERN = re.compile(
    r"^END-EXEC\b",
    flags=re.IGNORECASE,
)

# One-line: MOVE <source> TO <host> OF <DCLGROUP>
MOVE_TO_HOST_OF_GROUP_PATTERN = re.compile(
    r"^MOVE\s+(?P<source>.+?)\s+TO\s+"
    r"(?P<host>[A-Z][A-Z0-9-]*)\s+OF\s+"
    r"(?P<group>DCL[A-Z0-9-]+)\.?$",
    flags=re.IGNORECASE,
)

# Wrapped: "MOVE <source>" (first physical line of a split move).
MOVE_SOURCE_ONLY_PATTERN = re.compile(
    r"^MOVE\s+(?P<source>[A-Z0-9][A-Z0-9-]*)\.?$",
    flags=re.IGNORECASE,
)

# Wrapped continuation: "TO <host> OF <DCLGROUP>".
TO_HOST_OF_GROUP_PATTERN = re.compile(
    r"^TO\s+(?P<host>[A-Z][A-Z0-9-]*)\s+OF\s+"
    r"(?P<group>DCL[A-Z0-9-]+)\.?$",
    flags=re.IGNORECASE,
)