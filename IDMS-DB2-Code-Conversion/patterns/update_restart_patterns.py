from __future__ import annotations

import re


WORKING_STORAGE_SECTION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?WORKING-STORAGE\s+SECTION\s*\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

LINKAGE_SECTION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?LINKAGE\s+SECTION\s*\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

PROCEDURE_DIVISION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?PROCEDURE\s+DIVISION\b.*?\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

END_PROGRAM_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?END\s+PROGRAM\s+[A-Z0-9_-]+\s*\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

READ_FLAT_FILE_HEADER_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?READ-FLAT-FILE\s*\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)

PARAGRAPH_HEADER_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s*)?[A-Z0-9][A-Z0-9-]*\s*\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)

COPY_INCLUDE_TOKEN_PATTERN_TEMPLATE = r"\bCOPY\s+{include_name}\s*\."

EXEC_SQL_INCLUDE_TOKEN_PATTERN_TEMPLATE = (
    r"\bEXEC\s+SQL\s+INCLUDE\s+{include_name}\s+END-EXEC\s*\."
)

MALFORMED_SQLERROR_END_EVALUATE_PATTERN = re.compile(
    r"\bPERFORM\s+SQLERROR\s*\.\s*END-EVALUATE\b",
    flags=re.IGNORECASE,
)

RESTART_COMMENT_PATTERN = re.compile(
    r"\bRESTART\b|\bRECHERCHE\s+FFRECAB\b",
    flags=re.IGNORECASE,
)

OLD_RESTART_IF_PATTERN = re.compile(
    r"\bIF\s+SW-[A-Z0-9-]*REC[A-Z0-9-]*\s*=\s*['\"]Y['\"]",
    flags=re.IGNORECASE,
)

OLD_PREREAD_IF_EOF_PATTERN = re.compile(
    r"\bIF\s+NOT\s+(?P<switch>[A-Z][A-Z0-9-]*)\s*=\s*['\"]Y['\"]",
    flags=re.IGNORECASE,
)

OLD_PERFORM_UNTIL_EOF_PATTERN = re.compile(
    r"\bPERFORM\s+(?P<paragraph>[A-Z0-9-]+)\s+UNTIL\s+"
    r"(?P<switch>[A-Z0-9-]+)\s*=\s*['\"]Y['\"]",
    flags=re.IGNORECASE,
)

MOVE_TO_RESTART_FAMILY_PATTERN = re.compile(
    r"\bTO\s+[A-Z0-9-]+-FF(?:-[A-Z0-9-]+)?(?:\s+OF\s+[A-Z0-9-]+)?\b",
    flags=re.IGNORECASE,
)

FFRECAB_REFERENCE_PATTERN = re.compile(
    r"\bFFRECAB\b",
    flags=re.IGNORECASE,
)

EXEC_SQL_START_PATTERN = re.compile(
    r"^\s*EXEC\s+SQL\b",
    flags=re.IGNORECASE,
)

END_EXEC_PATTERN = re.compile(
    r"^\s*END-EXEC\s*\.",
    flags=re.IGNORECASE,
)

EVALUATE_SQLCODE_PATTERN = re.compile(
    r"^\s*EVALUATE\s+SQLCODE\b",
    flags=re.IGNORECASE,
)

END_EVALUATE_PATTERN = re.compile(
    r"^\s*END-EVALUATE\s*\.",
    flags=re.IGNORECASE,
)

STOP_RUN_PATTERN = re.compile(
    r"^\s*STOP\s+RUN\s*\.",
    flags=re.IGNORECASE,
)