from __future__ import annotations

import re

# Regex patterns for CHAR-literal quoting.
#
# Regex only. No business rules, conversion rules, file paths, program names,
# DB2 table names, DCLGEN names, copybook names, or host variables.

EXEC_SQL_START_PATTERN = re.compile(
    r"^EXEC\s+SQL\b",
    flags=re.IGNORECASE,
)

END_EXEC_PATTERN = re.compile(
    r"^END-EXEC\b",
    flags=re.IGNORECASE,
)

# One-line: MOVE <digits> TO <host> OF <DCLGROUP>
# Captures an UNQUOTED numeric literal moved to a DCLGEN host reference.
MOVE_NUMLIT_TO_HOST_OF_GROUP_PATTERN = re.compile(
    r"^MOVE\s+(?P<literal>[0-9]+)\s+TO\s+"
    r"(?P<host>[A-Z][A-Z0-9-]*)\s+OF\s+"
    r"(?P<group>DCL[A-Z0-9-]+)\.?$",
    flags=re.IGNORECASE,
)

# Wrapped continuation line: TO <host> OF <DCLGROUP>
# (the MOVE <digits> verb is on the previous physical line).
TO_HOST_OF_GROUP_PATTERN = re.compile(
    r"^TO\s+(?P<host>[A-Z][A-Z0-9-]*)\s+OF\s+"
    r"(?P<group>DCL[A-Z0-9-]+)\.?$",
    flags=re.IGNORECASE,
)

# A bare "MOVE <digits>" line (first half of a wrapped MOVE).
MOVE_NUMLIT_ONLY_PATTERN = re.compile(
    r"^MOVE\s+(?P<literal>[0-9]+)\.?$",
    flags=re.IGNORECASE,
)