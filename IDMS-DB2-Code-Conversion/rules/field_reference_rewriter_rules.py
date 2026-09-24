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

# LOCATION: rules/field_reference_rewriter_rules.py
# ACTION: APPEND at the end of the file

#
# ---- Fixed-format safety (appended)
#
# A qualified rewrite is almost always LONGER than what it replaces:
#
#     DA-CPTA-FORM-AS OF VMBFAS         25 characters
#     DA-CPTAFS-479BFAS OF DCLDZBFASTV  32 characters
#
# Substituting that into the whole record pushed the right sequence
# number from column 73 to column 80. Downstream passes then read the
# first displaced digit as part of the body and emitted
#
#     AND HELP-DA-CPTAFS-479BFAS NOT = '00000000') OR 0
#
# Rewriting is therefore confined to columns 8-72 and the record is
# reassembled from its original sequence areas.
ENFORCE_FIXED_FORMAT_REWRITE = True

# A rewritten body that no longer fits 65 columns is wrapped at word
# boundaries rather than truncated or allowed to overflow.
ALLOW_REWRITE_WRAPPING = True

FIELD_REFERENCE_GEOMETRY_MESSAGES = {
    "wrapped": (
        "Field reference: rewritten statement exceeded column 72 and was "
        "wrapped onto {count} line(s)."
    ),
    "refused": (
        "Field reference: rewritten statement cannot be represented in "
        "columns 8-72 and was left unchanged for manual review: {body}"
    ),
}