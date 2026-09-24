# LOCATION: src/idms_db2_phase2/composers/output_write/output_write_block_finder.py
# ACTION: CREATE NEW FILE
"""Walks the PROCEDURE DIVISION and yields candidate IF blocks.

Read-only discovery. It knows how to find an IF / END-IF pair and which
paragraph that pair sits in; it knows nothing about WRITE statements,
paragraph naming or whether a block is worth extracting.

Candidates are yielded in source order, so the caller can try each in
turn and stop at the first it accepts.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from idms_db2_phase2.composers.output_write.output_write_line_utils import (
    OutputWriteLineUtils,
)
from idms_db2_phase2.composers.output_write.output_write_scanner import (
    OutputWriteScanner,
)

UNNAMED_PARAGRAPH = "(unnamed)"


@dataclass(frozen=True)
class CandidateBlock:
    """One IF / END-IF pair inside a PROCEDURE DIVISION paragraph."""

    if_index: int = -1
    end_index: int = -1
    paragraph: str = ""

    @property
    def body_start(self) -> int:
        """First line of the guarded body.

        The IF line itself is never moved, which is why the guard must
        prove the condition does not span lines before any extraction
        is attempted.
        """
        return self.if_index + 1

    @property
    def source(self) -> str:
        return self.paragraph or UNNAMED_PARAGRAPH

    def body(self, lines: list[str]) -> list[str]:
        return lines[self.body_start:self.end_index]


class OutputWriteBlockFinder:
    """Finds every IF / END-IF pair in the PROCEDURE DIVISION."""

    def __init__(
        self,
        line_utils: OutputWriteLineUtils | None = None,
        scanner: OutputWriteScanner | None = None,
    ) -> None:
        self.lines = line_utils or OutputWriteLineUtils()
        self.scanner = scanner or OutputWriteScanner(self.lines)

    # ----------------------------------------------------------- public
    def candidates(self, lines: list[str]) -> Iterator[CandidateBlock]:
        """Every complete IF block, in source order.

        Stops at the first division boundary after the PROCEDURE
        DIVISION, so a LINKAGE or nested program can never be reached.
        """
        start = self.scanner.procedure_division_index(lines)
        if start < 0:
            return

        index = start + 1
        paragraph = ""

        while index < len(lines):
            logical = self.lines.logical(lines[index])

            if self.lines.is_division_boundary(logical):
                return

            header = self.lines.paragraph_name(lines[index])
            if header:
                paragraph = header
                index += 1
                continue

            if not self.scanner.is_condition_start(logical):
                index += 1
                continue

            end_index = self.scanner.matching_end_if(lines, index)
            if end_index >= 0:
                yield CandidateBlock(
                    if_index=index,
                    end_index=end_index,
                    paragraph=paragraph,
                )

            index += 1


__all__ = ["UNNAMED_PARAGRAPH", "CandidateBlock", "OutputWriteBlockFinder"]