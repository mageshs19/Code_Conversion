# LOCATION: rules/output_write_paragraph_rules.py
# ACTION: CREATE NEW FILE

"""Output write paragraph extraction rules.

Constants only. No regex, no runtime logic, no program / record / table /
cursor / paragraph / host variable names.

Manual reference shape:

    PERFORM 830-CLOSE-DZEVEFC1

    IF NOT SW-STATUS-D = 'Y'
       IF WS-STATUS = 'C'
          PERFORM WRITE-UITRECORD
          ADD 1 TO WS-NB-OUTPUT-COUNT
       END-IF
    END-IF.

    WRITE-UITRECORD.
        INITIALIZE UITRECORD
        MOVE ... TO ...
        WRITE UITRECORD.
"""

from __future__ import annotations

# =====================================================================
# Master switch
# =====================================================================
ENFORCE_OUTPUT_WRITE_PARAGRAPH = True

# =====================================================================
# Generated paragraph name
# =====================================================================
# Derived from the COBOL record written, never hardcoded:
#     WRITE UITRECORD  ->  WRITE-UITRECORD
WRITE_PARAGRAPH_TEMPLATE = "WRITE-{record}"
WRITE_PARAGRAPH_HEADER_TEMPLATE = "{paragraph}."
PERFORM_TEMPLATE = "PERFORM {paragraph}"

# =====================================================================
# Extraction safety
# =====================================================================
# A block is extracted only when it contains exactly this many WRITE
# statements. Two writes in one guard is a business decision, not a
# formatting one, and must stay where the programmer put it.
REQUIRED_WRITE_COUNT = 1

# Minimum executable body lines that make extraction worthwhile.
MINIMUM_BODY_LINES = 2

# Maximum lines scanned forward when matching an IF to its END-IF.
IF_SCAN_LIMIT = 200

# Maximum extraction passes over one program.
EXTRACTION_PASS_LIMIT = 8

# Single-word lines that end in a period but are NOT paragraph headers.
SCOPE_TERMINATOR_WORDS = frozenset(
    {
        "CONTINUE", "EXIT", "GOBACK", "STOP",
        "END-EXEC", "END-EVALUATE", "END-IF", "END-PERFORM",
        "END-READ", "END-SEARCH", "END-STRING", "END-WRITE",
    }
)

# =====================================================================
# Layout
# =====================================================================
IND_STATEMENT = "    "        # column 12, Area B
PARAGRAPH_TERMINATOR = "."
BLANK_LINE = ""

# Page eject placed before the generated paragraph, matching the manual
# reference separation between major paragraphs.
EMIT_PAGE_EJECT_BEFORE_PARAGRAPH = True
PAGE_EJECT_INDICATOR = "/"

# =====================================================================
# Counter increment
# =====================================================================
# The manual reference counts written records at the CALL SITE, not
# inside the write paragraph, so the counter reflects guard decisions.
EMIT_OUTPUT_COUNTER_INCREMENT = True
OUTPUT_COUNTER_NAME = "WS-NB-OUTPUT-COUNT"
COUNTER_ADD_TEMPLATE = "ADD 1 TO {name}"

# =====================================================================
# Diagnostics
# =====================================================================
OUTPUT_WRITE_PARAGRAPH_MESSAGES = {
    "extracted": (
        "Output write: extracted record population from {source} into "
        "paragraph {paragraph}."
    ),
    "counter_added": (
        "Output write: added {counter} increment at the {paragraph} "
        "call site."
    ),
    "skipped_multiple_writes": (
        "Output write: {source} holds {count} WRITE statements; "
        "extraction skipped."
    ),
    "skipped_name_taken": (
        "Output write: paragraph {paragraph} already exists; "
        "extraction skipped."
    ),
    "skipped_too_small": (
        "Output write: block in {source} is too small to extract."
    ),
}