from __future__ import annotations

import re


PROGRAM_RE = re.compile(
    r"\bPROGRAM-ID\s*\.\s*([A-Z0-9_-]+)\s*\.",
    flags=re.IGNORECASE | re.DOTALL,
)

SELECT_RE = re.compile(
    r"\bSELECT\s+([A-Z0-9_-]+)\s+ASSIGN\s+TO\s+([A-Z0-9_-]+)\s*\.",
    flags=re.IGNORECASE | re.DOTALL,
)

READ_RE = re.compile(
    r"\bREAD\s+([A-Z0-9_-]+)(?:\s+INTO\s+([A-Z0-9_-]+))?",
    flags=re.IGNORECASE | re.DOTALL,
)

COPY_RE = re.compile(
    r"\bCOPY\s+([A-Z0-9_-]+)\s*\.",
    flags=re.IGNORECASE,
)

FIELD_USE_RE = re.compile(
    r"\b([A-Z][A-Z0-9-]+)\s+(?:OF|IN)\s+([A-Z][A-Z0-9-]+)\b",
    flags=re.IGNORECASE,
)

MOVE_FIELD_RE = re.compile(
    r"\bMOVE\s+([A-Z][A-Z0-9-]+)\b",
    flags=re.IGNORECASE,
)

SELECT_LINE_RE = re.compile(
    r"\bSELECT\s+([A-Z0-9_-]+)\s+ASSIGN\s+TO\s+([A-Z0-9_-]+)\s*\.",
    flags=re.IGNORECASE,
)

FD_LINE_RE = re.compile(
    r"\bFD\s+([A-Z0-9_-]+)\b",
    flags=re.IGNORECASE,
)

RECORD_CONTAINS_RE = re.compile(
    r"\bRECORD\s+CONTAINS\s+(\d+)\s+CHARACTERS\b",
    flags=re.IGNORECASE,
)

FD_RECORD_01_RE = re.compile(
    r"^\s*01\s+([A-Z0-9_-]+)\b",
    flags=re.IGNORECASE,
)

SECTION_END_RE = re.compile(
    r"\b(WORKING-STORAGE|LINKAGE|PROCEDURE)\s+SECTION\b",
    flags=re.IGNORECASE,
)

READ_LINE_RE = re.compile(
    r"\bREAD\s+([A-Z0-9_-]+)(?:\s+INTO\s+([A-Z0-9_-]+))?",
    flags=re.IGNORECASE,
)

EOF_UNTIL_RE = re.compile(
    r"\bUNTIL\s+([A-Z][A-Z0-9-]*)\s*=\s*['\"]Y['\"]",
    flags=re.IGNORECASE,
)

EOF_IF_RE = re.compile(
    r"\bIF\s+(?:NOT\s+)?([A-Z][A-Z0-9-]*)\s*=\s*['\"]Y['\"]",
    flags=re.IGNORECASE,
)

EOF_MOVE_RE = re.compile(
    r"\bMOVE\s+['\"]Y['\"]\s+TO\s+([A-Z][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)

PIC_LENGTH_RE = re.compile(
    r"[X9]$(\d+)$|[X9]",
    flags=re.IGNORECASE,
)