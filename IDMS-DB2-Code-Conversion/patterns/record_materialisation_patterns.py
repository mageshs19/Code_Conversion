# LOCATION: patterns/record_materialisation_patterns.py
# ACTION: CREATE NEW FILE
"""Regex for IDMS record materialisation. Regex only."""

from __future__ import annotations

import re

_NAME = r"[A-Z][A-Z0-9-]*"

# MOVE VMBFAS TO F-FORM
WHOLE_RECORD_MOVE_PATTERN = re.compile(
    rf"^MOVE\s+(?P<record>{_NAME})\s+TO\s+(?P<target>{_NAME})\s*\.?\s*$",
    flags=re.IGNORECASE,
)

# 05  F-FORM                PIC X(478).
TARGET_FIELD_PATTERN_TEMPLATE = (
    r"^(?P<level>\d{{2}})\s+(?P<name>{name})\s+"
    r"(?P<picture>PIC(?:TURE)?\s+[^.]+)\.?\s*$"
)

# "03 NR-CIO-FORM-AS"  ->  level 03, name NR-CIO-FORM-AS
COBOL_ZONE_PATTERN = re.compile(
    rf"^\s*(?P<level>\d{{2}})?\s*(?P<name>{_NAME})\s*$",
    flags=re.IGNORECASE,
)

# "05 CT-RK-TGOOD REDEFINES CT-RK-TGDSV"
COBOL_ZONE_REDEFINES_PATTERN = re.compile(
    rf"^\s*(?P<level>\d{{2}})?\s*(?P<name>{_NAME})\s+REDEFINES\s+"
    rf"(?P<base>{_NAME})\s*$",
    flags=re.IGNORECASE,
)

# PIC 9(8) COMP-3   /   PIC X(4)   /   PIC S9(13)V99 COMP-3
PICTURE_PATTERN = re.compile(
    r"PIC(?:TURE)?\s+(?P<picture>[SXA9VZ0-9()\-.,/+*]+)"
    r"(?P<usage>\s+(?:COMP-3|COMP|COMPUTATIONAL-3|COMPUTATIONAL"
    r"|BINARY|PACKED-DECIMAL|DISPLAY))?",
    flags=re.IGNORECASE,
)

# Repeat factor inside a picture: 9(8), X(478)
PICTURE_REPEAT_PATTERN = re.compile(r"(?P<symbol>[SXA9Z])$(?P<count>\d+)$")

WORKING_STORAGE_PATTERN = re.compile(
    r"^WORKING-STORAGE\s+SECTION\s*\.", flags=re.IGNORECASE,
)
PROCEDURE_DIVISION_PATTERN = re.compile(
    r"^PROCEDURE\s+DIVISION\b", flags=re.IGNORECASE,
)
# LOCATION: patterns/record_materialisation_patterns.py
# ACTION: APPEND at the end of the file

# Every character-position symbol of a PICTURE clause, with its optional
# repeat count.
#
#     X(478)   -> symbol X, repeat 478
#     XXX      -> symbol X three times, repeat None
#     S9(13)V99-> 9 with repeat 13, then 9 twice
#
# Used to size a PICTURE from the LINE, so the byte count never depends
# on which group another pattern happened to capture.
PICTURE_SYMBOL_PATTERN = re.compile(
    r"(?P<symbol>[X9AZ])(?:$(?P<repeat>\d+)$)?",
    flags=re.IGNORECASE,
)

# Everything after the PIC / PICTURE keyword on a data description entry.
PICTURE_CLAUSE_PATTERN = re.compile(
    r"\bPIC(?:TURE)?\s+(?:IS\s+)?(?P<clause>[^.]*)",
    flags=re.IGNORECASE,
)


# LOCATION: patterns/record_materialisation_patterns.py
# ACTION: REPLACE the previously appended block with this one

# One PICTURE symbol together with its optional repeat count.
#
# The existing PICTURE_SYMBOL_PATTERN captures the symbol ONLY. It has no
# 'repeat' group, so every clause using (n) collapsed to the number of
# literal symbols:
#
#     PIC 9999    -> 4    correct, four literal symbols
#     PIC 9(7)    -> 1    WRONG, the (7) was never read
#     PIC X(478)  -> 1    WRONG
#
# F-FORM therefore measured 1 byte, the length guard refused a 432-byte
# VMBFAS layout as "longer than the 1 byte F-FORM declares", and roughly
# 400 lines of generated output were discarded on every run.
#
# Whitespace inside the parentheses is tolerated: the mapping workbook
# contains clauses written as 'PIC X(4 )'.
PICTURE_SYMBOL_REPEAT_PATTERN = re.compile(
    r"(?P<symbol>[X9AZ])"
    r"(?:\s*$\s*(?P<repeat>\d+)\s*$)?",
    flags=re.IGNORECASE,
)

# The PICTURE clause itself, bounded so that no trailing clause is read
# as picture symbols.
#
#     77  USERABEN  PIC X(8)  VALUE 'USERABEN'.
#
# An unbounded capture would count the A of VALUE and the A of USERABEN
# and report 10 bytes instead of 8.
PICTURE_AFTER_KEYWORD_PATTERN = re.compile(
    r"\bPIC(?:TURE)?\s+(?:IS\s+)?"
    r"(?P<picture>.+?)"
    r"(?=\s+(?:USAGE|COMPUTATIONAL-3|COMPUTATIONAL|COMP-3|COMP"
    r"|PACKED-DECIMAL|BINARY|DISPLAY|VALUE|OCCURS|REDEFINES)\b"
    r"|\s*\.\s*$|$)",
    flags=re.IGNORECASE,
)

# USAGE clause on the same entry, used only to halve a COMP-3 length.
USAGE_CLAUSE_PATTERN = re.compile(
    r"\b(?:USAGE\s+(?:IS\s+)?)?"
    r"(?P<usage>COMPUTATIONAL-3|COMP-3|PACKED-DECIMAL|COMPUTATIONAL"
    r"|COMP|BINARY|DISPLAY)\b",
    flags=re.IGNORECASE,
)