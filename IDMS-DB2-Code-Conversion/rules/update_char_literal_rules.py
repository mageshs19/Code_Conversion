from __future__ import annotations

# Rules for quoting numeric literals moved into character DB2 host variables.
#
# Constants only. No regex patterns, parser logic, service logic, program names,
# DB2 table names, DCLGEN names, or host variable names belong here.

UPDATE_CHAR_LITERAL_RULES = [
    "When a bare numeric literal is moved to a CHAR/VARCHAR DB2 host variable, "
    "quote the literal (manual standard).",
    "CHAR/VARCHAR detection is DCLGEN-driven (db2_type or COBOL PIC X).",
    "Do not quote literals moved to numeric hosts.",
    "Do not touch SQL host references inside EXEC SQL blocks.",
    "Do not hardcode program names, DB2 tables, columns, DCLGEN groups, "
    "or host variables.",
]

# DB2 datatype prefixes that indicate a character column.
CHAR_DB2_TYPE_PREFIXES = ("CHAR", "VARCHAR", "GRAPHIC", "VARGRAPHIC")

# COBOL picture prefix that indicates a character (alphanumeric) field.
CHAR_PICTURE_PREFIX = "X"

# Diagnostic emitted when a literal is quoted.
CHAR_LITERAL_QUOTED_DIAGNOSTIC = (
    "Update CHAR literal: quoted numeric literal moved to CHAR host variable."
)