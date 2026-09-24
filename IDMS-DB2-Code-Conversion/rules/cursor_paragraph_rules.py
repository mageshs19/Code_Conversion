# LOCATION: rules/cursor_paragraph_rules.py
# ACTION: REPLACE ENTIRE FILE

"""Cursor paragraph generation rules.

This module contains constants only.

No regex patterns, parser logic, generator logic, or hardcoded program,
record, table, cursor, or host variable names belong here.

Layout follows the COBOL team's manual reference program:

    *---------------------------------------------------------------*
    *    OPEN CURSOR
    *---------------------------------------------------------------*
     710-OPEN-DZBEFFC1.
    D    DISPLAY '710-OPEN-DZBEFFC1.'
         MOVE 710    TO SQL-LOCATION

         EXEC SQL
           OPEN DZBEFFC1
         END-EXEC

         EVALUATE SQLCODE
           WHEN ZERO
                SET DZBEFFC1-NOT-EOC TO TRUE
           WHEN OTHER
                DISPLAY 'ERROR WHILE OPENING CURSOR DZBEFFC1'
                PERFORM SQLERROR
         END-EVALUATE
         .
"""

from __future__ import annotations

# =====================================================================
# Fixed process / error paragraph names (COBOL-shop standard)
# =====================================================================
SQL_ERROR_PARAGRAPH_NAME = "SQLERROR"
LEGACY_SQL_ERROR_PARAGRAPH_NAME = "SQL-ERROR"
SQL_LOCATION_FIELD = "SQL-LOCATION"

# =====================================================================
# Termination rule
# =====================================================================
# The paragraph body is ONE COBOL sentence. No period on MOVE, END-EXEC
# or END-EVALUATE; a single period on its own line closes the paragraph.
# A period inside EVALUATE closes the scope early and orphans
# END-EVALUATE.
LONE_PERIOD = "."

# =====================================================================
# SQL-LOCATION form
# =====================================================================
# RESOLVED by the COBOL team's manual reference program:
#
#     MOVE 710    TO SQL-LOCATION
#
# SQL-LOCATION is supplied by the SQLERRWS copybook, NOT declared by the
# converter.
#
# code_review CHK-05 already accepts both forms:
#     MOVE_SQL_LOCATION = re.compile(
#         r"^MOVE\s+(?:'[^']*'|\d+)\s+TO\s+SQL-LOCATION\s*\.?$"
#     )
# so flipping this to True does not regress the review.
SQL_LOCATION_USES_PARAGRAPH_NUMBER = True
SQL_LOCATION_NUMBER_PAD = "    "

# The converter must NOT declare SQL-LOCATION: the copybook owns it.
DECLARE_SQL_LOCATION_FIELD = False

# =====================================================================
# Body indents, relative to column 8
# =====================================================================
IND_STATEMENT = "    "            # column 12
IND_SQL_BODY = "      "           # column 14
IND_SQL_INTO = "       "          # column 15
IND_SQL_INTO_NEXT = "          "  # column 18
IND_WHEN = "      "               # column 14
IND_WHEN_BODY = "           "     # column 19
IND_WHEN_BODY_CONT = "                                 "  # DISPLAY align

# =====================================================================
# COBOL tokens
# =====================================================================
TOKEN_EXEC_SQL = "EXEC SQL"
TOKEN_END_EXEC = "END-EXEC"
TOKEN_EVALUATE_SQLCODE = "EVALUATE SQLCODE"
TOKEN_END_EVALUATE = "END-EVALUATE"
TOKEN_WHEN_ZERO = "WHEN ZERO"
TOKEN_WHEN_100 = "WHEN 100"
TOKEN_WHEN_OTHER = "WHEN OTHER"
TOKEN_CONTINUE = "CONTINUE"
TOKEN_INTO = "INTO"
TOKEN_HOST_SEPARATOR = ", "

# =====================================================================
# Cursor operations and flag suffixes
# =====================================================================
CURSOR_OPERATIONS = ("OPEN", "FETCH", "CLOSE")
CURSOR_EOC_SUFFIX = "-EOC"
CURSOR_NOT_EOC_SUFFIX = "-NOT-EOC"
CURSOR_FLAG_TEMPLATE = "WS-{cursor}-FLAG"

# =====================================================================
# Generated statement templates
# =====================================================================
SQL_LOCATION_NUMBER_TEMPLATE = "MOVE {number}{pad}TO {field}"
SQL_LOCATION_NAME_TEMPLATE = "MOVE '{name}' TO {field}"
PARAGRAPH_HEADER_TEMPLATE = "{paragraph}."
OPEN_STATEMENT_TEMPLATE = "OPEN {cursor}"
FETCH_STATEMENT_TEMPLATE = "FETCH {cursor}"
CLOSE_STATEMENT_TEMPLATE = "CLOSE {cursor}"
SET_NOT_EOC_TEMPLATE = "SET {cursor}{suffix} TO TRUE"
SET_EOC_TEMPLATE = "SET {cursor}{suffix} TO TRUE"
DISPLAY_ERROR_TEMPLATE = "DISPLAY '{text}'"
PERFORM_TEMPLATE = "PERFORM {paragraph}"
COMMENT_BLOCK_TEMPLATE = "*{title:<62}*"
INTO_FIRST_TEMPLATE = "INTO :{group}.{host}"
INTO_NEXT_TEMPLATE = ", :{group}.{host}"

# =====================================================================
# Manual reference banners
# =====================================================================
BANNER_RULE = (
    "*---------------------------------------------------------------*"
)
BANNER_TITLE_TEMPLATE = "*    {title}"

BANNER_OPEN_CURSOR = "OPEN CURSOR"
BANNER_FETCH_CURSOR = "FETCH CURSOR"
BANNER_CLOSE_CURSOR = "CLOSE CURSOR"

EMIT_PARAGRAPH_BANNERS = True

# =====================================================================
# Debug (column 7 = 'D') trace lines
# =====================================================================
EMIT_DEBUG_TRACE_LINES = True
DEBUG_INDICATOR = "D"
DEBUG_TRACE_TEMPLATE = "DISPLAY '{paragraph}.'"

# Sentinel prefix used to mark a body line that must carry the 'D'
# indicator in column 7. The fixed-format writer strips it.
DEBUG_SENTINEL = "\x01D"

# =====================================================================
# Join-key diagnostics inside a child FETCH WHEN OTHER branch
# =====================================================================
# The manual reference displays every parent join key before performing
# SQLERROR so the failing row can be identified in the job log.
EMIT_JOIN_KEY_DIAGNOSTICS = True
JOIN_KEY_DISPLAY_TEMPLATE = "DISPLAY '{label} = ' {host}"
JOIN_KEY_QUALIFIER_TEMPLATE = "OF {group}"
JOIN_KEY_LABEL_WIDTH = 13

# =====================================================================
# Error display text
# =====================================================================
ERROR_OPEN_TEMPLATE = "ERROR WHILE OPENING CURSOR {cursor}"
ERROR_FETCH_TEMPLATE = "ERROR WHILE FETCHING CURSOR {cursor}"
ERROR_CLOSE_TEMPLATE = "ERROR WHILE CLOSING CURSOR {cursor}"

# =====================================================================
# Diagnostics
# =====================================================================
DIAG_NO_CURSOR_OPERATIONS = (
    "DB2 cursor paragraphs: no cursor operations found."
)
DIAG_BLOCK_EXISTS = (
    "DB2 cursor paragraphs: generated cursor paragraph block already exists."
)
DIAG_GENERATED_TEMPLATE = (
    "DB2 cursor paragraphs: generated {count} cursor paragraph set(s)."
)
DIAG_NO_HOST_VARIABLES_TEMPLATE = (
    "DB2 cursor paragraphs: no FETCH host variables resolved for "
    "cursor {cursor} record {record} table {table}."
)

ENFORCE_FETCH_PROLOGUE = True

INITIALIZE_HOST_GROUP_TEMPLATE = "INITIALIZE {group}."

# Separator between a host group and its field in a FETCH INTO item,
# e.g. :DCLDZBFASTV.DA-CPTAFS-479BFAS
HOST_GROUP_SEPARATOR = "."
HOST_REFERENCE_PREFIX = ":"
ENFORCE_SQL_LOCATION_IN_ERROR_BRANCH = True
EMIT_FETCH_KEY_DIAGNOSTICS = True

# How many leading INTO hosts to display. The manual shows five. An
# unbounded list would bury the failure in the job log.
FETCH_KEY_DIAGNOSTIC_LIMIT = 5

# Rendered as: DISPLAY '<label> : ' <field> OF <group>
FETCH_KEY_DISPLAY_TEMPLATE = "DISPLAY '{label} : ' {host}"
FETCH_KEY_LABEL_WIDTH = 18
FETCH_KEY_HOST_TEMPLATE = "{field} OF {group}"

# Body window is columns 8-72. A DISPLAY that does not fit is split at
# the OF keyword and the continuation is aligned under the operand,
# matching the manual. Truncation is never acceptable: a cut data-name
# does not compile.
FETCH_KEY_BODY_END_COLUMN = 72

FETCH_KEY_MESSAGES = {
    "emitted": (
        "Cursor paragraphs: {cursor} FETCH error branch displays "
        "{count} fetched column(s) before PERFORM {paragraph}."
    ),
    "no_hosts": (
        "Cursor paragraphs: {cursor} FETCH error branch has no "
        "qualified host to display; generic error text only."
    ),
}