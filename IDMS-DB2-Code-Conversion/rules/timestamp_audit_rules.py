# LOCATION: rules/timestamp_audit_rules.py
# ACTION: REPLACE ENTIRE FILE

"""
Timestamp and audit rules.

This file contains timestamp/audit rule constants and generation templates
only. No parser, service, transformer, generator, resolver, or composer logic
belongs here.

No program name, table name, DCLGEN group name, or business field name is
hardcoded. The generator supplies only the dynamic program-id value.
"""

TIMESTAMP_AUDIT_RULES = [
    "Sheet Mapping decides DB2 table and column names.",
    "DCLGEN supplies COBOL host variable spelling and group names.",
    "DCLGEN must not introduce audit fields absent from Sheet Mapping.",
    "For UPDATE flows, generate TS_UPDATE and USER-ID moves only.",
    "TS_CREATE is insert-only and is not generated for update-only flows.",
    "Timestamp paragraph must be a safe paragraph with a terminating boundary.",
]

AUDIT_COLUMN_PREFIXES = [
    "TS_CREATE",
    "TS_UPDATE",
    "ID_USERID",
    "NR_USERID",
    "ID_USER",
    "NR_USER",
    "NS_IDMSKEY",
]

UPDATE_AUDIT_COLUMN_PREFIXES = [
    "TS_UPDATE",
    "ID_USERID",
    "NR_USERID",
    "ID_USER",
    "NR_USER",
]

INSERT_EXCLUDE_AUDIT_PREFIXES = [
    "TS_UPDATE",
]

DATE_COLUMN_PREFIXES = [
    "DA_",
    "DT_",
]

# --- Timestamp generation templates (manual standard) ---
#
# TS-SYSTEM receives FUNCTION CURRENT-DATE output.
# TS-TIMESTAMP is a flat formatted timestamp with separator markers.
#
# The generator supplies only the dynamic value:
#   - program_id  (for CS-PROGRAM)

TIMESTAMP_WS_MARKER = "DB2 GENERATED TIMESTAMP AND AUDIT WORKING STORAGE"

TIMESTAMP_CS_PROGRAM_TEMPLATE = (
    "01 CS-PROGRAM                 PIC X(8) VALUE '{program_id:<8}'."
)

TIMESTAMP_WS_LINES = [
    "01 WS-TIMESTAMP-FIELDS.",
    "    05 TS-SYSTEM.",
    "       10  CC                  PIC X(2).",
    "       10  YY                  PIC X(2).",
    "       10  MM                  PIC X(2).",
    "       10  DD                  PIC X(2).",
    "       10  HH                  PIC X(2).",
    "       10  MI                  PIC X(2).",
    "       10  SS                  PIC X(2).",
    "       10  TT                  PIC X(2).",
    "       10  FILLER              PIC X(13).",
    "    05 TS-TIMESTAMP.",
    "       10  CC                  PIC X(2).",
    "       10  YY                  PIC X(2).",
    "       10  TE-MARKER1          PIC X    VALUE '-'.",
    "       10  MM                  PIC X(2).",
    "       10  TE-MARKER2          PIC X    VALUE '-'.",
    "       10  DD                  PIC X(2).",
    "       10  TE-MARKER3          PIC X    VALUE '-'.",
    "       10  HH                  PIC X(2).",
    "       10  TE-MARKER4          PIC X    VALUE '.'.",
    "       10  MI                  PIC X(2).",
    "       10  TE-MARKER5          PIC X    VALUE '.'.",
    "       10  SS                  PIC X(2).",
    "       10  TE-MARKER6          PIC X    VALUE '.'.",
    "       10  TT                  PIC X(2).",
    "       10  NNNN                PIC 9(04) VALUE 0.",
]

# Field pairs moved from TS-SYSTEM into TS-TIMESTAMP (manual standard).
TIMESTAMP_MOVE_FIELDS = (
    "CC",
    "YY",
    "MM",
    "DD",
    "HH",
    "MI",
    "SS",
    "TT",
)

# Paragraph body templates. {paragraph_name} is the only dynamic value.
TIMESTAMP_PARAGRAPH_HEADER_TEMPLATE = "{paragraph_name}."
TIMESTAMP_PARAGRAPH_SOURCE_MOVE = (
    "     MOVE FUNCTION CURRENT-DATE            TO TS-SYSTEM."
)
TIMESTAMP_PARAGRAPH_FIELD_MOVE_TEMPLATE = (
    "     MOVE {field} OF TS-SYSTEM{pad}TO {field} OF TS-TIMESTAMP"
)
TIMESTAMP_PARAGRAPH_DISPLAY = "     DISPLAY 'TIMESTAMP: ' TS-TIMESTAMP"
TIMESTAMP_PARAGRAPH_TERMINATOR = "     ."

# Column width at which the 'TO' part aligns in generated timestamp moves.
TIMESTAMP_MOVE_ALIGN_COLUMN = 38

# LOCATION: rules/timestamp_audit_rules.py
# ACTION: APPEND these two constants

# Fallback program-id used only when no target PROGRAM-ID is supplied.
# Kept in rules/ so no program name is hardcoded inside generator logic.
TIMESTAMP_DEFAULT_PROGRAM_ID = "DB2PGM"

# COBOL PIC X(8) program-id field length (CS-PROGRAM width).
TIMESTAMP_PROGRAM_ID_LENGTH = 8

