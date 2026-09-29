# LOCATION: zowe/zowe_resolver.py
# ACTION: REPLACE ENTIRE FILE
"""Works out what ONE IDMS program needs.

CORRECTION - every dependency was invisible

The patterns were anchored at the start of the physical line, but a
mainframe source member is FIXED FORMAT:

    001234     COPY VMBZ270I.                              01234000
    |----|     |----------------------------------------|  |------|
    cols 1-6   cols 8-72 body                              cols 73-80

so "^\\s*COPY" never matched and the program reported zero copybooks
and no subschema. Every line is now reduced to its BODY before any
pattern is applied, and comment lines (indicator * or / in column 7)
are dropped.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from zowe.zowe_patterns import (
    COPY_IDMS_RECORD_PATTERN,
    DB_WITHIN_PATTERN,
    FIXED_SEQUENCE_PATTERN,
    IDMS_VERB_RECORD_PATTERN,
    PLAIN_COPY_PATTERN,
    RECORD_VERSION_SUFFIX_PATTERN,
)
from zowe.zowe_rules import (
    BODY_END_COLUMN,
    BODY_START_COLUMN,
    COMMENT_INDICATORS,
    DCLGEN_MEMBER_TEMPLATE,
    DCLGEN_PREFIX,
    DCLGEN_RECORD_TAIL_LENGTH,
    DCLGEN_SUFFIX,
    INDICATOR_COLUMN,
)

# Verb operands that are never record names.
_NOT_A_RECORD = {
    "CURRENT", "WITHIN", "USING", "SET", "AREA", "RECORD",
    "DB", "IDMS", "ALL", "SELECTIVE", "NEXT", "FIRST", "LAST",
}


def logical_body(line: str) -> str:
    """The COBOL body of one physical line, or '' for a comment.

    Tolerates free-format source: a line with no 6-digit sequence area
    is returned as-is.
    """
    text = str(line or "").rstrip("\n").rstrip()
    if not text:
        return ""

    if not FIXED_SEQUENCE_PATTERN.match(text):
        stripped = text.lstrip()
        if stripped[:1] in COMMENT_INDICATORS:
            return ""
        return text

    indicator = text[INDICATOR_COLUMN] if len(text) > INDICATOR_COLUMN else " "
    if indicator in COMMENT_INDICATORS:
        return ""

    return text[BODY_START_COLUMN:BODY_END_COLUMN].rstrip()


def logical_text(source_text: str) -> str:
    """Whole member reduced to executable COBOL bodies."""
    bodies = [logical_body(line) for line in str(source_text or "").splitlines()]
    return "\n".join(body for body in bodies if body)


def base_record_name(record: str) -> str:
    """VMBTL03-R01 -> VMBTL03. A view suffix is not part of the name."""
    name = str(record or "").strip().upper()
    return RECORD_VERSION_SUFFIX_PATTERN.sub("", name)


def dclgen_member_for(record: str) -> str:
    """VMBEVEF -> DZEVEFTV,  VMBTL03-R01 -> DZTL03TV"""
    name = base_record_name(record).replace("-", "")
    if len(name) < DCLGEN_RECORD_TAIL_LENGTH:
        return ""
    return DCLGEN_MEMBER_TEMPLATE.format(
        prefix=DCLGEN_PREFIX,
        tail=name[-DCLGEN_RECORD_TAIL_LENGTH:],
        suffix=DCLGEN_SUFFIX,
    )


@dataclass
class ProgramDependencies:
    program: str = ""
    copybooks: list[str] = field(default_factory=list)
    records: list[str] = field(default_factory=list)
    dclgens: list[str] = field(default_factory=list)
    subschema: str = ""


def _unique(values) -> list[str]:
    out: list[str] = []
    for value in values:
        name = str(value or "").strip().upper()
        if name and name not in out:
            out.append(name)
    return out


def resolve_dependencies(program: str, source_text: str) -> ProgramDependencies:
    text = logical_text(source_text)

    copybooks = _unique(
        match.group("member") for match in PLAIN_COPY_PATTERN.finditer(text)
    )

    records = _unique(
        match.group("record") for match in COPY_IDMS_RECORD_PATTERN.finditer(text)
    )
    for match in IDMS_VERB_RECORD_PATTERN.finditer(text):
        name = match.group("record").strip().upper()
        if name and name not in _NOT_A_RECORD and name not in records:
            records.append(name)

    subschema = ""
    match = DB_WITHIN_PATTERN.search(text)
    if match:
        subschema = match.group("subschema").strip().upper()

    dclgens = _unique(dclgen_member_for(record) for record in records)

    return ProgramDependencies(
        program=str(program or "").strip().upper(),
        copybooks=copybooks,
        records=records,
        dclgens=dclgens,
        subschema=subschema,
    )