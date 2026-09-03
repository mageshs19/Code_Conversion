from __future__ import annotations

# SQLCODE wrapper cleanup constants. Constants only.
# No regex, no runtime logic, no program/record/table names.

# --- Detection / comment texts ---
OUTER_IF_TEXT = "IF NOT SQLCODE = 100"
INNER_IF_TEXT = "IF SQLCODE = 100"
REMOVED_OBTAIN_NEXT_TEXT = (
    "DB2: REMOVED REDUNDANT OBTAIN NEXT AFTER CURSOR EOC LOOP"
)
CLEANUP_COMMENT_TEXT = (
    "DB2: Removed redundant SQLCODE wrapper after cursor EOC loop."
)

# --- COBOL tokens ---
TOKEN_IF = "IF "
TOKEN_END_IF = "END-IF"
TOKEN_MOVE = "MOVE "
TOKEN_TO = "TO "
TOKEN_OF_DCL = " OF DCL"
DB2_COMMENT_PREFIX = "DB2:"
COMMENT_INDICATOR = "*"
PAGE_INDICATOR = "/"

# --- Indentation / geometry ---
BASE_INDENT = "    "        # 4 spaces
CHILD_INDENT = "        "   # 8 spaces
CONTINUATION_INDENT = "    "  # 4 spaces added for wrapped continuations
BODY_WIDTH = 65
FULL_LINE_WIDTH = 80
SEQUENCE_AREA_WIDTH = 6
INDICATOR_COLUMN = 6       # 0-based index of the indicator char
BODY_START_COLUMN = 7
BODY_END_COLUMN = 72
RIGHT_SEQUENCE_START = 72
RIGHT_SEQUENCE_END = 80

# --- Look-ahead windows ---
MARKER_LOOKAHEAD = 8       # rows scanned after outer IF for the removed marker
INNER_IF_LOOKAHEAD = 12    # rows scanned for the inner IF SQLCODE = 100

# --- Comment prefix set (for skip decisions) ---
COMMENT_PREFIXES = ("*", "/")