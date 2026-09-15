# LOCATION: rules/manual_reference_rules.py
# ACTION: CREATE NEW FILE
"""Manual COBOL reference standard constants.

Single source of truth for everything the COBOL team's manual reference
program dictates about generated output shape.

Constants only. No regex, no runtime logic, no program / record / table /
cursor / host variable names.
"""

from __future__ import annotations

# ---------------------------------------------------------------------
# Identification Division
# ---------------------------------------------------------------------
REPLACE_IDENTIFICATION_HEADER = True

IDENTIFICATION_RULE_LINE = "*========================"
PROGRAM_ID_TEMPLATE = "PROGRAM-ID.   {program_id}."
AUTHOR_TEMPLATE = "AUTHOR.       {author}."
DATE_WRITTEN_TEMPLATE = "DATE-WRITTEN. {date_written}."

# Supplied by config, never hardcoded in a generator.
DEFAULT_AUTHOR = ""
DEFAULT_DATE_WRITTEN = ""

# ---------------------------------------------------------------------
# Comment banners
# ---------------------------------------------------------------------
# Full-width rule used above and below a generated paragraph group.
BANNER_RULE = "*---------------------------------------------------------------*"
BANNER_TITLE_TEMPLATE = "*    {title}"

BANNER_OPEN_CURSOR = "OPEN CURSOR"
BANNER_FETCH_CURSOR = "FETCH CURSOR"
BANNER_CLOSE_CURSOR = "CLOSE CURSOR"

# Section banner used inside WORKING-STORAGE.
SECTION_BANNER_TEMPLATE = "*---- {title} {fill}*"
SECTION_BANNER_WIDTH = 64
SECTION_BANNER_FILL = "-"

SECTION_DB2_INCLUDE = "INCLUDE FOR DB2"
SECTION_DB2_VIEWS = "INCLUDE VIEWS"

# Short banner used inside PROCEDURE DIVISION (4 stars, no closing star).
INLINE_BANNER_PREFIX = "****"
INLINE_BANNER_TEMPLATE = "**** {text}"

INLINE_BANNER_PARENT_READ = "READ PARENT TABLE {table}"
INLINE_BANNER_CHILD_READ = "READ CHILD TABLE {table}"
INLINE_BANNER_WRITE_CHECK = (
    "CHECK THE CONDITION FOR WRITING THE RECORD INTO OUTPUT FILE"
)

# Cursor declaration banner.
CURSOR_BANNER_TITLE_TEMPLATE = "* DECLARE CURSOR FOR {short_name} TABLE"
CURSOR_BANNER_UNDERLINE = "* ------------------------------"
CURSOR_BANNER_BLANK = "*"

# ---------------------------------------------------------------------
# Debug (column 7 = 'D') trace lines
# ---------------------------------------------------------------------
EMIT_DEBUG_TRACE_LINES = True
DEBUG_INDICATOR = "D"
DEBUG_TRACE_TEMPLATE = "DISPLAY '{paragraph}.'"

# ---------------------------------------------------------------------
# COMMIT policy
# ---------------------------------------------------------------------
# A retrieval program declares every cursor FOR READ ONLY and therefore
# never needs an explicit COMMIT. Emitting one is harmless at run time
# but diverges from the manual reference.
EMIT_COMMIT_IN_RETRIEVAL = False

# ---------------------------------------------------------------------
# Page eject
# ---------------------------------------------------------------------
# The manual reference separates major business paragraphs with a page
# eject in the indicator column.
EMIT_PAGE_EJECT_BETWEEN_PARAGRAPHS = True
PAGE_EJECT_INDICATOR = "/"