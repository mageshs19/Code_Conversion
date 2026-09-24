# LOCATION: src/idms_db2_phase2/composers/output_write/output_write_scanner.py
# ACTION: CREATE NEW FILE
"""Block discovery for the output write extraction.

Read-only: locates the PROCEDURE DIVISION, matches IF / END-IF pairs,
finds WRITE records and paragraph boundaries. Rewrites nothing.
"""

from __future__ import annotations

from idms_db2_phase2.composers.output_write.output_write_line_utils import (
    OutputWriteLineUtils,
)
from patterns.output_write_paragraph_patterns import (
    END_IF_PATTERN,
    IF_START_PATTERN,
    PERFORM_WRITE_PARAGRAPH_PATTERN,
    PROCEDURE_DIVISION_PATTERN,
    WRITE_STATEMENT_PATTERN,
)
from rules.output_write_paragraph_rules import IF_SCAN_LIMIT


class OutputWriteScanner:
    """Finds the boundaries the extraction needs."""

    def __init__(
        self,
        line_utils: OutputWriteLineUtils | None = None,
    ) -> None:
        self.lines = line_utils or OutputWriteLineUtils()

    # ------------------------------------------------------ divisions
    def procedure_division_index(self, lines: list[str]) -> int:
        for index, line in enumerate(lines):
            if PROCEDURE_DIVISION_PATTERN.match(self.lines.logical(line)):
                return index
        return -1

    # ---------------------------------------------------------- scope
    @staticmethod
    def is_condition_start(logical: str) -> bool:
        return bool(IF_START_PATTERN.match(logical))

    def matching_end_if(self, lines: list[str], if_index: int) -> int:
        """Index of the END-IF that closes the IF at if_index."""
        depth = 0
        limit = min(len(lines), if_index + IF_SCAN_LIMIT)

        for index in range(if_index, limit):
            line = lines[index]

            if self.lines.is_skippable(line):
                continue

            logical = self.lines.logical(line)
            if not logical:
                continue

            if index > if_index and self.lines.paragraph_name(line):
                return -1

            if IF_START_PATTERN.match(logical):
                depth += 1
                continue

            if END_IF_PATTERN.match(logical):
                depth -= 1
                if depth == 0:
                    return index

        return -1

    # ---------------------------------------------------------- write
    def write_records(self, body: list[str]) -> list[str]:
        out: list[str] = []

        for line in body:
            if self.lines.is_skippable(line):
                continue
            match = WRITE_STATEMENT_PATTERN.match(self.lines.logical(line))
            if match:
                out.append(match.group("record"))

        return out

    def already_extracted(self, body: list[str]) -> bool:
        """True when an earlier pass already replaced this block."""
        return any(
            PERFORM_WRITE_PARAGRAPH_PATTERN.match(self.lines.logical(line))
            for line in body
        )

    # ------------------------------------------------------ paragraph
    def paragraph_end_index(self, lines: list[str], start: int) -> int:
        """Index just past the paragraph containing `start`."""
        for index in range(start + 1, len(lines)):
            if self.lines.paragraph_name(lines[index]):
                return index
            if self.lines.is_division_boundary(
                self.lines.logical(lines[index])
            ):
                return index
        return len(lines)


__all__ = ["OutputWriteScanner"]