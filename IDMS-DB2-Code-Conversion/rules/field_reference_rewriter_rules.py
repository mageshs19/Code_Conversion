from __future__ import annotations

"""
Rules/constants for IDMS field reference rewriting.

This module contains constants only.
No regex patterns, transformer logic, DB2 table names, DCLGEN names, or host
variables belong here.
"""


FIELD_REFERENCE_REWRITE_RULES = [
    "Rewrite qualified FIELD OF RECORD and FIELD IN RECORD references when Sheet Mapping and DCLGEN metadata resolve safely.",
    "Rewrite bare references only when active record context is strong.",
    "Do not rewrite inside EXEC SQL blocks.",
    "Do not rewrite string literals.",
    "Do not rewrite non-PROCEDURE DIVISION business declarations.",
    "Protect date/work/control prefixes for bare references only.",
    "Do not hardcode program names, record names, DB2 tables, DB2 columns, DCLGEN groups, or host variables.",
]


PROTECTED_BARE_PREFIXES = (
    "WS-",
    "WK-",
    "W-",
    "SW-",
    "UIT-",
    "OUT-",
    "ES-",
    "D-",
    "DATE",
    "SQL",
    "DCL",
    "L-",
    "LS-",
    "PARAM",
    "ERROR-",
    "USER",
    "CS-",
    "TS-",
    "DA-",
    "HR-",
    "HELP-",
)


DCLGEN_GROUP_PREFIX = "DCL"

# --- Host-reference formatting constants (used by the host resolver) ---
# Separator between a host field and its DCLGEN group.
HOST_GROUP_SEPARATOR = " OF "

# Leading character stripped from a raw host reference (e.g. ":HOST").
HOST_REFERENCE_LEADING_CHAR = ":"

# Format template for a resolved "HOST OF GROUP" reference.
HOST_OF_GROUP_TEMPLATE = "{host} OF {group}"

# Number of parts expected when splitting on the OF keyword.
HOST_OF_SPLIT_PART_COUNT = 2