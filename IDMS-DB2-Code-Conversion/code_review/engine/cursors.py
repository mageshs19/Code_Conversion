"""Shared cursor parsing for checks.

Recognises the two shapes the converter emits:

    EXEC SQL
        DECLARE <cursor> CURSOR WITH HOLD FOR
        SELECT ... FROM <table> ... FOR READ ONLY
    END-EXEC.

    710-OPEN-<cursor>.
    720-FETCH-<cursor>.
    730-CLOSE-<cursor>.

Read-only. Knows nothing about standards or wording.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from code_review.engine import sql_blocks as sql

DECLARE = re.compile(
    r"\bDECLARE\s+(?P<cursor>[A-Z][A-Z0-9-]*)\s+CURSOR\b"
)
PARAGRAPH = re.compile(
    r"^(?P<number>\d{3,6})-"
    r"(?P<operation>OPEN|FETCH|CLOSE)-"
    r"(?P<cursor>[A-Z0-9][A-Z0-9-]*)\.$"
)
PERFORM = re.compile(
    r"^PERFORM\s+(?P<name>[A-Z0-9][A-Z0-9-]*)\b(?P<rest>.*)$"
)
CURSOR_VERB = re.compile(
    r"\b(?P<operation>OPEN|FETCH|CLOSE)\s+(?P<cursor>[A-Z][A-Z0-9-]*)\b"
)

# COBOL scope terminators that look like a paragraph header because they
# are a single word followed by a period. These are language facts, not
# site standards, so they live here rather than in standards/. A caller
# may pass a fuller list through stop_words.
SCOPE_TERMINATORS = frozenset({
    "CONTINUE", "END-EXEC", "END-EVALUATE", "END-IF", "END-PERFORM",
    "END-READ", "END-SEARCH", "END-STRING", "END-WRITE", "EXIT",
    "GOBACK", "STOP",
})


@dataclass(frozen=True)
class CursorParagraph:
    """One generated cursor paragraph header."""

    number: int
    operation: str
    cursor: str
    line_number: int
    name: str

    def render(self) -> str:
        return str(self)

    def __str__(self) -> str:
        """One readable evidence line.

        The Recorder turns anything that is not a Line or Finding into
        Finding(text=str(item)), so without this the whole dataclass repr
        would land in the report.
        """
        return f"line {self.line_number:>5} : {self.name}"


def declared_cursors(view) -> dict[str, sql.SqlBlock]:
    """Cursor name -> its DECLARE block."""
    out: dict[str, sql.SqlBlock] = {}
    for block in sql.sql_blocks(view):
        if block.verb != "DECLARE":
            continue
        match = DECLARE.search(block.text)
        if match:
            out.setdefault(match.group("cursor").upper(), block)
    return out


def declare_blocks(view) -> list[sql.SqlBlock]:
    return [b for b in sql.sql_blocks(view) if b.verb == "DECLARE"]


def cursor_paragraphs(view) -> list[CursorParagraph]:
    """Every generated cursor paragraph header, in source order."""
    out: list[CursorParagraph] = []
    for line in view.code:
        logical = sql.norm(line.logical)
        match = PARAGRAPH.match(logical)
        if not match:
            continue
        out.append(CursorParagraph(
            number=int(match.group("number")),
            operation=match.group("operation").upper(),
            cursor=match.group("cursor").upper(),
            line_number=line.number,
            name=logical.rstrip("."),
        ))
    return out


def paragraph_sets(view) -> dict[str, dict[str, CursorParagraph]]:
    """Cursor name -> {OPEN: para, FETCH: para, CLOSE: para}."""
    out: dict[str, dict[str, CursorParagraph]] = {}
    for para in cursor_paragraphs(view):
        out.setdefault(para.cursor, {})[para.operation] = para
    return out


def performed_names(view) -> dict[str, list]:
    """Performed paragraph name -> the lines that perform it."""
    out: dict[str, list] = {}
    for line in view.code:
        match = PERFORM.match(sql.norm(line.logical))
        if match:
            out.setdefault(match.group("name").upper(), []).append(line)
    return out


def cursors_used(view, operation: str) -> set[str]:
    """Cursor names appearing in an EXEC SQL OPEN / FETCH / CLOSE."""
    wanted = str(operation or "").upper()
    out: set[str] = set()
    for block in sql.sql_blocks(view):
        if block.verb != wanted:
            continue
        match = CURSOR_VERB.search(block.text)
        if match:
            out.add(match.group("cursor").upper())
    return out


def is_paragraph_header(logical: str, stop_words) -> bool:
    """A single word plus a period that is not a scope terminator.

    END-EXEC. and CONTINUE. look identical to a paragraph header at the
    token level. Treating them as one truncates every paragraph body at
    the first EXEC SQL block.
    """
    text = str(logical or "").strip()
    if not text.endswith(".") or " " in text:
        return False
    name = text[:-1]
    if not name:
        return False
    if name in SCOPE_TERMINATORS:
        return False
    return name not in (stop_words or frozenset())


def paragraph_body(view, para: CursorParagraph, stop_words=None) -> list[str]:
    """Normalised lines of a paragraph, up to the next paragraph header."""
    words = stop_words if stop_words is not None else frozenset()
    code = view.code
    start = next(
        (
            index for index, line in enumerate(code)
            if line.number == para.line_number
        ),
        -1,
    )
    if start < 0:
        return []

    out: list[str] = []
    for line in code[start + 1:]:
        logical = sql.norm(line.logical)
        if PARAGRAPH.match(logical):
            break
        if is_paragraph_header(logical, words):
            break
        out.append(logical)
    return out