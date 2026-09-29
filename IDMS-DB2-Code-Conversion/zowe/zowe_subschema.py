# LOCATION: zowe/zowe_subschema.py
# ACTION: REPLACE ENTIRE FILE
"""Element records of a logical record, read from the subschema source.

A logical record has no DCLGEN; its ELEMENT records do.

PARSING IS STRUCTURAL, NOT LEXICAL

The ELEMENTS name list ends at the first line that starts a new subschema
DDL clause. Clause keywords come from rules/, so no business name and no
natural-language word appears in this module. A line that is not a pure
name list is rejected as a whole rather than mined for tokens, so prose
inside a COMMENTS or DESCRIPTION clause can never leak in.
"""

from __future__ import annotations

from pathlib import Path

from zowe.zowe_env import setting
from zowe.zowe_patterns import (
    BLOCK_END_PATTERN,
    ELEMENT_TOKEN_PATTERN,
    ELEMENTS_ARE_PATTERN,
    LOGICAL_RECORD_PATTERN,
    NAME_LIST_ONLY_PATTERN,
    SUBSCHEMA_CLAUSE_HEAD_PATTERN,
)
from zowe.zowe_rules import (
    ELEMENT_NAME_MIN_LENGTH,
    NAME_RECORD_PREFIX,
    SUBSCHEMA_CLAUSE_KEYWORDS,
    SUBSCHEMA_ELEMENT_NOISE,
    TEXT_ENCODING,
)


def record_prefix() -> str:
    """Optional application filter. Blank accepts every record name."""
    return setting("", NAME_RECORD_PREFIX, "").strip().upper()


def starts_new_clause(line: str) -> bool:
    """True when the line begins a new subschema DDL clause."""
    match = SUBSCHEMA_CLAUSE_HEAD_PATTERN.match(str(line or ""))
    if not match:
        return False
    return match.group("head").strip().upper() in SUBSCHEMA_CLAUSE_KEYWORDS


def is_name_list(line: str) -> bool:
    """True when the line contains ONLY names and list separators.

    Prose carries characters a name list never does, so one test
    rejects the whole line instead of filtering token by token.
    """
    return bool(NAME_LIST_ONLY_PATTERN.match(str(line or "").strip()))


def is_element_name(token: str, prefix: str) -> bool:
    name = str(token or "").strip().upper()
    if len(name) < ELEMENT_NAME_MIN_LENGTH:
        return False
    if name in SUBSCHEMA_ELEMENT_NOISE:
        return False
    if name in SUBSCHEMA_CLAUSE_KEYWORDS:
        return False
    if prefix and not name.startswith(prefix):
        return False
    return True


def _collect(target: list[str], text: str, prefix: str) -> None:
    for token in ELEMENT_TOKEN_PATTERN.findall(str(text or "")):
        name = token.strip().upper()
        if is_element_name(name, prefix) and name not in target:
            target.append(name)


def parse_element_records(text: str) -> dict[str, list[str]]:
    """{logical record name: [element record names]}"""
    prefix = record_prefix()
    records: dict[str, list[str]] = {}
    current = ""
    collecting = False

    for raw_line in str(text or "").splitlines():
        line = raw_line.rstrip()

        match = LOGICAL_RECORD_PATTERN.match(line)
        if match:
            current = match.group("lr").strip().upper()
            records.setdefault(current, [])
            collecting = False
            continue

        if not current:
            continue

        if BLOCK_END_PATTERN.match(line):
            collecting = False
            continue

        elements = ELEMENTS_ARE_PATTERN.match(line)
        if elements:
            collecting = True
            _collect(records[current], elements.group("rest"), prefix)
            continue

        if not collecting:
            continue

        # A new DDL clause, or anything that is not a pure name list,
        # ends the ELEMENTS clause.
        if starts_new_clause(line) or not is_name_list(line):
            collecting = False
            continue

        _collect(records[current], line, prefix)

    return records


def element_records_for(path: Path, logical_record: str) -> list[str]:
    """Element records of ONE logical record. Empty when not found."""
    target = Path(path)
    if not target.is_file():
        return []

    records = parse_element_records(
        target.read_text(encoding=TEXT_ENCODING, errors="replace")
    )

    wanted = str(logical_record or "").strip().upper()
    if wanted in records:
        return records[wanted]

    # A program may name the base record without its view suffix.
    base = wanted.split("-")[0]
    for name, elements in records.items():
        if name.split("-")[0] == base:
            return elements

    return []