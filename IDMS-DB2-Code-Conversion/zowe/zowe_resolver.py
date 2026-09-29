# LOCATION: zowe/zowe_resolver.py
# ACTION: CREATE NEW FILE
"""Works out what ONE IDMS program needs.

Copybooks come from COPY statements. DCLGEN members are DERIVED from the
IDMS record names the program touches. The subschema comes from the
SCHEMA SECTION DB clause.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from zowe.zowe_patterns import (
    COPY_IDMS_RECORD_PATTERN,
    DB_WITHIN_PATTERN,
    IDMS_VERB_RECORD_PATTERN,
    PLAIN_COPY_PATTERN,
)
from zowe.zowe_rules import (
    DCLGEN_MEMBER_TEMPLATE,
    DCLGEN_PREFIX,
    DCLGEN_RECORD_TAIL_LENGTH,
    DCLGEN_SUFFIX,
)

# Verb operands that are never record names.
_NOT_A_RECORD = {
    "CURRENT", "WITHIN", "USING", "SET", "AREA", "RECORD",
    "DB", "IDMS", "ALL", "SELECTIVE",
}


def dclgen_member_for(record: str) -> str:
    """VMBEVEF -> DZEVEFTV"""
    name = str(record or "").strip().upper().replace("-", "")
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
    text = str(source_text or "")

    copybooks = _unique(
        m.group("member") for m in PLAIN_COPY_PATTERN.finditer(text)
    )

    records = _unique(
        m.group("record") for m in COPY_IDMS_RECORD_PATTERN.finditer(text)
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