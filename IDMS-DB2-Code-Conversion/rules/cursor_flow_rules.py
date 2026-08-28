"""
Cursor flow rule constants.

This file contains cursor flow constant values only.
No regex patterns and no runtime logic belong here.
Rules belong in rules/, patterns in patterns/.
"""

# Maximum number of lines to look ahead when correlating a cursor OPEN
# with its matching FETCH and business loop.
LOOKAHEAD_LIMIT = 120

# Maximum look-ahead when locating the UNTIL SQLCODE = 100 clause.
UNTIL_LOOKAHEAD_LIMIT = 10

# Dotted lines that must never be treated as paragraph headers.
NON_PARAGRAPH_DOTTED_LINES = {
    "CONTINUE.",
    "END-EXEC.",
    "END-EVALUATE.",
    "END-IF.",
    "END-PERFORM.",
    "EXIT.",
    "GOBACK.",
    "STOP.",
}

# Statement prefixes that disqualify a line from being a paragraph header.
NON_PARAGRAPH_HEADER_PREFIXES = (
    "WHEN ",
    "END-",
    "EXEC ",
    "MOVE ",
    "DISPLAY ",
    "PERFORM ",
    "SET ",
    "OPEN ",
    "CLOSE ",
    "FETCH ",
    "INTO",
    ":",
)

# Comment replacement inserted where a redundant OBTAIN NEXT is removed.
REMOVED_OBTAIN_NEXT_COMMENT = (
    "* DB2: Removed redundant OBTAIN NEXT after cursor EOC loop."
)