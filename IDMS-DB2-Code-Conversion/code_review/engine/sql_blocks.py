"""Shared EXEC SQL block parsing for checks.

Fixed-format COBOL splits one logical SQL statement across many physical
lines, and pads with whitespace. Checks that reason about SQL need a
normalised, whole-statement view, so that logic lives here once instead of
being copied into every check.

Read-only. Knows nothing about standards or wording.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

WS_RUN = re.compile(r"\s+")
EXEC_SQL = "EXEC SQL"
END_EXEC = "END-EXEC"
VERB = re.compile(r"^EXEC\s+SQL\s+(?P<verb>[A-Z-]+)\b")
EVIDENCE_WIDTH = 90


def norm(text: str) -> str:
    """Uppercase, trimmed, internal whitespace runs collapsed."""
    return WS_RUN.sub(" ", str(text or "").strip().upper())


def logical_statements(lines: list[str]) -> list[str]:
    """Logical statements, with EXEC SQL ... END-EXEC. joined into one entry.

    Order is preserved one-to-one for non-SQL lines, so positional
    reasoning stays valid.
    """
    out: list[str] = []
    buffer: list[str] = []
    inside = False

    for raw in lines:
        line = norm(raw)

        if not inside and line.startswith(EXEC_SQL):
            inside = True
            buffer = [line]
            if END_EXEC in line:
                out.append(" ".join(buffer))
                inside, buffer = False, []
            continue

        if inside:
            buffer.append(line)
            if END_EXEC in line:
                out.append(" ".join(buffer))
                inside, buffer = False, []
            continue

        out.append(line)

    if buffer:
        out.append(" ".join(buffer))
    return out


@dataclass(frozen=True)
class SqlBlock:
    """One EXEC SQL ... END-EXEC. statement."""

    first_index: int
    last_index: int
    text: str
    lines: list = field(default_factory=list)

    @property
    def verb(self) -> str:
        match = VERB.match(self.text)
        return match.group("verb") if match else ""

    @property
    def line_number(self) -> int:
        return self.lines[0].number if self.lines else 0

    def has(self, keyword: str) -> bool:
        return f" {norm(keyword)} " in f" {self.text} "

    def render(self) -> str:
        return str(self)

    def __str__(self) -> str:
        """One readable evidence line.

        The Recorder turns anything that is not a Line or Finding into
        Finding(text=str(item)), so without this a block would print its
        whole dataclass repr into the report.
        """
        body = self.text
        if len(body) > EVIDENCE_WIDTH:
            body = f"{body[:EVIDENCE_WIDTH]}..."
        return f"line {self.line_number:>5} : {body}"


def sql_blocks(view) -> list[SqlBlock]:
    """Every EXEC SQL block in the code lines of a CobolView."""
    code = view.code
    out: list[SqlBlock] = []
    buffer: list = []
    start = -1
    inside = False

    for index, line in enumerate(code):
        logical = norm(line.logical)

        if not inside and logical.startswith(EXEC_SQL):
            inside = True
            start = index
            buffer = [line]
            if END_EXEC in logical:
                out.append(_build(start, index, buffer))
                inside, buffer, start = False, [], -1
            continue

        if inside:
            buffer.append(line)
            if END_EXEC in logical:
                out.append(_build(start, index, buffer))
                inside, buffer, start = False, [], -1

    if buffer and start >= 0:
        out.append(_build(start, len(code) - 1, buffer))
    return out


def _build(first: int, last: int, lines: list) -> SqlBlock:
    text = norm(" ".join(line.logical for line in lines))
    return SqlBlock(
        first_index=first, last_index=last, text=text, lines=list(lines),
    )


def targets_restart(block: SqlBlock, hints) -> bool:
    """True when a block reads or writes a restart or control table.

    Restart SQL is owned by CHK-19, CHK-20 and CHK-21. The business
    conversion checks must exclude it, or one deferred decision is
    reported several times and blocks delivery twice over.
    """
    text = block.text
    return any(str(hint or "").upper() in text for hint in (hints or ()))


def lines_before(view, block: SqlBlock, count: int) -> list[str]:
    """Normalised code lines immediately before a block."""
    code = view.code
    start = max(0, block.first_index - int(count))
    return [norm(line.logical) for line in code[start:block.first_index]]


def lines_after(view, block: SqlBlock, count: int) -> list[str]:
    """Normalised code lines immediately after a block."""
    code = view.code
    end = min(len(code), block.last_index + 1 + int(count))
    return [norm(line.logical) for line in code[block.last_index + 1:end]]