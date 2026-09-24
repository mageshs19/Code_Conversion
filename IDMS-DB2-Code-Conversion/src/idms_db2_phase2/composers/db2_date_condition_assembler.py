# LOCATION: src/idms_db2_phase2/composers/db2_date_condition_assembler.py
# ACTION: CREATE NEW FILE

"""Assembles one COBOL IF condition out of its physical lines.

WHY THIS EXISTS
---------------
Db2DateFieldDetector and Db2DateComparisonRewriter both used to inspect a
single physical line. A hand-written COBOL condition routinely spans
several:

    IF (DA-CPTAFS-479BFAS OF DCLDZBFASTV < DA-ARCH-YMD
       AND DA-CPTAFS-479BFAS OF DCLDZBFASTV NOT = '00000000') OR
       (DA-CRFMAS-479BFAS OF DCLDZBFASTV < DA-ARCH-YMD AND
       DA-CPTAFS-479BFAS OF DCLDZBFASTV = '00000000')

A per-line matcher structurally cannot see that, so the date pass was
skipped and the program shipped comparing a 10-byte DD.MM.CCYY host
against an 8-byte CCYYMMDD field.

WHERE A CONDITION ENDS
----------------------
Scanning stops at the FIRST of:

  * parentheses balanced AND the line does not end on AND / OR / NOT AND
    the next line does not begin with AND / OR / (,
  * a line that starts a COBOL statement verb,
  * CONDITION_SCAN_LIMIT lines.

Hitting the limit is reported, never guessed around.

Read-only. Assembles and measures; rewrites nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from idms_db2_phase2.composers.db2_date_line_utils import Db2DateLineUtils
from patterns.db2_date_patterns import (
    CONDITION_CONTINUATION_PATTERN,
    END_EXEC_PATTERN,
    EXEC_SQL_START_PATTERN,
    IF_START_PATTERN,
    STATEMENT_START_PATTERN,
    TRAILING_BOOLEAN_PATTERN,
)
from rules.db2_date_conversion_rules import CONDITION_SCAN_LIMIT

OPEN_PAREN = "("
CLOSE_PAREN = ")"


@dataclass
class ConditionSpan:
    """One IF condition and the physical lines that carry it."""

    start_index: int = -1
    end_index: int = -1          # inclusive
    indent: str = ""
    text: str = ""               # assembled, single space separated
    line_indexes: list[int] = field(default_factory=list)
    complete: bool = True

    @property
    def line_count(self) -> int:
        return len(self.line_indexes)


class Db2DateConditionAssembler:
    """Finds IF conditions and joins their physical lines."""

    def __init__(
        self,
        line_utils: Db2DateLineUtils | None = None,
    ) -> None:
        self.line_utils = line_utils or Db2DateLineUtils()

    #
    # Public entry point
    #
    def span_at(
        self,
        lines: list[str],
        index: int,
    ) -> ConditionSpan | None:
        """The condition starting at `index`, or None when it is not an IF."""
        if not 0 <= index < len(lines):
            return None

        logical = self.line_utils.logical(lines[index])

        if self.line_utils.is_comment_or_blank(logical):
            return None

        match = IF_START_PATTERN.match(logical)

        if not match:
            return None

        indent = match.group("indent") or ""
        first = str(match.group("rest") or "").strip()

        parts: list[str] = [first] if first else []
        used: list[int] = [index]
        depth = self._depth(first)
        previous = first

        cursor = index + 1
        scanned = 0
        complete = self._is_complete(previous, depth, lines, cursor)

        while not complete and scanned < CONDITION_SCAN_LIMIT:
            if cursor >= len(lines):
                break

            body = self.line_utils.logical(lines[cursor])

            if self.line_utils.is_comment_or_blank(body):
                cursor += 1
                continue

            scanned += 1
            parts.append(body.strip())
            used.append(cursor)
            depth += self._depth(body)
            previous = body
            cursor += 1

            complete = self._is_complete(previous, depth, lines, cursor)

        return ConditionSpan(
            start_index=index,
            end_index=used[-1],
            indent=indent,
            text=" ".join(part for part in parts if part).strip(),
            line_indexes=used,
            complete=complete,
        )

    def spans(self, lines: list[str]) -> list[ConditionSpan]:
        """Every IF condition in the program, EXEC SQL blocks excluded."""
        output: list[ConditionSpan] = []
        index = 0
        in_exec_sql = False

        while index < len(lines):
            logical = self.line_utils.logical(lines[index])

            if EXEC_SQL_START_PATTERN.match(logical):
                in_exec_sql = not END_EXEC_PATTERN.search(logical)
                index += 1
                continue

            if in_exec_sql:
                if END_EXEC_PATTERN.search(logical):
                    in_exec_sql = False
                index += 1
                continue

            span = self.span_at(lines, index)

            if span is None:
                index += 1
                continue

            output.append(span)
            index = span.end_index + 1

        return output

    #
    # Termination
    #
    def _is_complete(
        self,
        previous: str,
        depth: int,
        lines: list[str],
        cursor: int,
    ) -> bool:
        if depth > 0:
            return False

        if TRAILING_BOOLEAN_PATTERN.search(previous or ""):
            return False

        return not self._next_continues(lines, cursor)

    def _next_continues(self, lines: list[str], cursor: int) -> bool:
        index = cursor

        while index < len(lines):
            body = self.line_utils.logical(lines[index])

            if self.line_utils.is_comment_or_blank(body):
                index += 1
                continue

            if STATEMENT_START_PATTERN.match(body):
                return False

            return bool(CONDITION_CONTINUATION_PATTERN.match(body))

        return False

    @staticmethod
    def _depth(text: str) -> int:
        body = str(text or "")
        return body.count(OPEN_PAREN) - body.count(CLOSE_PAREN)


__all__ = ["ConditionSpan", "Db2DateConditionAssembler"]