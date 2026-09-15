"""Constants for the generated-COBOL safety cleanup passes.

This module contains constants only.
No regex patterns, parser logic, service logic, or hardcoded program,
record, table, cursor, or host variable names belong here.

Covers:
- paragraph sentence termination
- output-write placement relative to a child cursor loop
- Area B alignment of generated EXEC SQL / END-EXEC marker lines
"""

from __future__ import annotations

# --- Paragraph termination -------------------------------------------------
#
# A COBOL paragraph is one or more sentences. If the last executable line of
# a paragraph carries no period, the sentence runs into the next paragraph
# header and the compiler rejects the program.
PARAGRAPH_TERMINATOR = "."
ENFORCE_PARAGRAPH_TERMINATION = True

# --- Output-write placement ------------------------------------------------
#
# Manual reference shape:
#
#     PERFORM <open-child>
#     PERFORM <fetch-child> UNTIL <eoc> OR <early-stop-flag> = 'Y'
#     PERFORM <close-child>
#
#     IF NOT <early-stop-flag> = 'Y'
#        IF <status-field> = '<value>'
#           PERFORM <write-paragraph>
#        END-IF
#     END-IF.
#
# A guarded WRITE left inside the per-row paragraph fires once per fetched
# child row instead of once per parent row.
ENFORCE_OUTPUT_WRITE_AFTER_CHILD_LOOP = True

# Working-storage flag written by the child-fetch early-stop cleanup.
EARLY_STOP_FLAG = "SW-STATUS-D"
EARLY_STOP_VALUE = "'Y'"

# Guard emitted around a relocated write block. {flag} and {value} are
# supplied by the service from the constants above.
EARLY_STOP_GUARD_OPEN = "IF NOT {flag} = {value}"
EARLY_STOP_GUARD_CLOSE = "END-IF"

# Body indents, relative to column 8.
IND_STATEMENT = "    "        # column 12
IND_NESTED = "   "            # one nesting step

# Look-ahead limit when scanning a paragraph for its trailing write block.
WRITE_BLOCK_SCAN_LIMIT = 200

# --- Area B alignment of generated SQL markers -----------------------------
#
# CHK-06.07 measures every generated DB2 block line and requires an indent of
# at least 4 body spaces, i.e. physical column 12. The manual reference puts
# EXEC SQL, END-EXEC, EVALUATE SQLCODE and END-EVALUATE at column 12.
ALIGN_GENERATED_SQL_MARKERS_EVERYWHERE = True
SQL_MARKER_MIN_INDENT = 4
SQL_MARKER_INDENT = "    "

# --- Diagnostics -----------------------------------------------------------
SAFETY_MESSAGES = {
    "paragraph_terminated": (
        "Safety: closed unterminated sentence in paragraph {paragraph}."
    ),
    "write_block_moved": (
        "Safety: moved output write block from {source} to {target} after "
        "the child cursor loop."
    ),
    "sql_markers_aligned": (
        "Safety: aligned {count} generated EXEC SQL / END-EXEC marker "
        "line(s) to Area B."
    ),
}