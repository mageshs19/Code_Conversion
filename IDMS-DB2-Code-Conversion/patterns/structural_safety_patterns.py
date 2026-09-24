# LOCATION: patterns/structural_safety_patterns.py
# ACTION: REPLACE ENTIRE FILE
"""Regex for the structural safety passes. Regex only.

CORRECTION - numbered paragraphs were invisible
-----------------------------------------------
_NAME was [A-Z][A-Z0-9-]* , which requires a leading LETTER. Every
generated cursor paragraph is numbered:

    710-OPEN-DZBFASC1.
    720-FETCH-DZBFASC1.
    730-CLOSE-DZBFASC1.

None of them matched PARAGRAPH_HEADER_PATTERN, so the unreachable-code
guard was never disarmed and commented the whole generated block.

Two name classes are now declared. A DATA NAME must start with a letter.
A PARAGRAPH NAME may start with a digit.
"""

from __future__ import annotations

import re

# A COBOL data-name: must begin with a letter.
_DATA_NAME = r"[A-Z][A-Z0-9-]*"

# A COBOL paragraph / section name: may begin with a digit.
_PARAGRAPH_NAME = r"[A-Z0-9][A-Z0-9-]*"

# ---- conditions
IF_START_PATTERN = re.compile(r"^IF\b", flags=re.IGNORECASE)
END_IF_PATTERN = re.compile(r"^END-IF\s*\.?\s*$", flags=re.IGNORECASE)

# ---- data declarations
LEVEL_01_PATTERN = re.compile(
    rf"^01\s+(?P<name>{_DATA_NAME})\s*(?P<terminator>\.)?",
    flags=re.IGNORECASE,
)
SUBORDINATE_LEVEL_PATTERN = re.compile(
    rf"^(?P<level>0[2-9]|[1-4][0-9]|66|77|88)\s+(?P<name>{_DATA_NAME})\b",
    flags=re.IGNORECASE,
)
FD_PATTERN = re.compile(r"^FD\s+", flags=re.IGNORECASE)
FILE_SECTION_PATTERN = re.compile(
    r"^FILE\s+SECTION\s*\.", flags=re.IGNORECASE,
)
WORKING_STORAGE_PATTERN = re.compile(
    r"^WORKING-STORAGE\s+SECTION\s*\.", flags=re.IGNORECASE,
)
LINKAGE_SECTION_PATTERN = re.compile(
    r"^LINKAGE\s+SECTION\s*\.", flags=re.IGNORECASE,
)
PROCEDURE_DIVISION_PATTERN = re.compile(
    r"^PROCEDURE\s+DIVISION\b", flags=re.IGNORECASE,
)

# ---- record-layout evidence
RECORD_VERB_PATTERN = re.compile(
    rf"^(?P<verb>WRITE|READ|REWRITE|RELEASE|RETURN)\s+"
    rf"(?P<name>{_DATA_NAME})\b",
    flags=re.IGNORECASE,
)
WRITE_FROM_PATTERN = re.compile(
    rf"\bFROM\s+(?P<name>{_DATA_NAME})\b", flags=re.IGNORECASE,
)
READ_INTO_PATTERN = re.compile(
    rf"\bINTO\s+(?P<name>{_DATA_NAME})\b", flags=re.IGNORECASE,
)
MOVE_WHOLE_GROUP_PATTERN = re.compile(
    rf"^MOVE\s+(?:SPACE|SPACES|ZERO|ZEROES|ZEROS)\s+TO\s+"
    rf"(?P<name>{_DATA_NAME})\s*\.?\s*$",
    flags=re.IGNORECASE,
)

# ---- orphaned whole-record references
MOVE_BARE_SOURCE_PATTERN = re.compile(
    rf"^MOVE\s+(?P<name>{_DATA_NAME})\s+TO\s+"
    rf"(?P<target>{_DATA_NAME})\s*\.?\s*$",
    flags=re.IGNORECASE,
)
MOVE_BARE_TARGET_PATTERN = re.compile(
    rf"^MOVE\s+(?P<source>{_DATA_NAME})\s+TO\s+"
    rf"(?P<name>{_DATA_NAME})\s*\.?\s*$",
    flags=re.IGNORECASE,
)
QUALIFIER_PATTERN = re.compile(
    rf"\b(?:OF|IN)\s+(?P<record>{_DATA_NAME})\b", flags=re.IGNORECASE,
)

# ---- paragraph structure
PARAGRAPH_HEADER_PATTERN = re.compile(
    rf"^(?P<name>{_PARAGRAPH_NAME})\s*\.\s*$", flags=re.IGNORECASE,
)
SECTION_HEADER_PATTERN = re.compile(
    rf"^{_PARAGRAPH_NAME}\s+SECTION\s*\.\s*$", flags=re.IGNORECASE,
)
EXIT_STATEMENT_PATTERN = re.compile(
    r"^(?P<word>EXIT|GOBACK|STOP\s+RUN)\s*\.\s*$", flags=re.IGNORECASE,
)