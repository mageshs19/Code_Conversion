# LOCATION: zowe/zowe_subschema.py
# ACTION: CREATE NEW FILE
"""Element records of a logical record, read from the subschema source.

A logical record has no DCLGEN. Its ELEMENT records do.
"""

from __future__ import annotations

import re
from pathlib import Path

from zowe.zowe_rules import TEXT_ENCODING

LOGICAL_RECORD_PATTERN = re.compile(
    r"^\s*ADD\s+LOGICAL\s+RECORD\s+(?:NAME\s+IS\s+)?"
    r"(?P<lr>[A-Z0-9][A-Z0-9-]*)",
    flags=re.IGNORECASE,
)
ELEMENTS_ARE_PATTERN = re.compile(
    r"^\s*ELEMENTS?\s+ARE\b(?P<rest>.*)$", flags=re.IGNORECASE
)
ELEMENT_NAME_PATTERN = re.compile(r"[A-Z][A-Z0-9-]{2,}", flags=re.IGNORECASE)
BLOCK_END_PATTERN = re.compile(r"^\s*\.\s*$")

_KEYWORDS = {"ELEMENTS", "ARE", "IS", "NAME", "ADD", "LOGICAL", "RECORD"}


def _collect(target: list[str], text: str) -> None:
    for token in ELEMENT_NAME_PATTERN.findall(str(text or "")):
        name = token.strip().upper()
        if name not in _KEYWORDS and name not in target:
            target.append(name)


def parse_element_records(text: str) -> dict[str, list[str]]:
    """{logical record name: [element record names]}"""
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
            _collect(records[current], elements.group("rest"))
            continue

        if collecting:
            _collect(records[current], line)

    return records


def element_records_for(path: Path, logical_record: str) -> list[str]:
    """Element records of ONE logical record. Empty when not found."""
    if not Path(path).is_file():
        return []

    records = parse_element_records(
        Path(path).read_text(encoding=TEXT_ENCODING, errors="replace")
    )

    wanted = str(logical_record or "").strip().upper()
    if wanted in records:
        return records[wanted]

    base = wanted.split("-")[0]
    for name, elements in records.items():
        if name.split("-")[0] == base:
            return elements

    return []