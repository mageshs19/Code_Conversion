# LOCATION: src/idms_db2_phase2/composers/cursor_close_guarantee/paragraph_index.py
# ACTION: CREATE NEW FILE

"""Paragraph discovery and navigation over generated COBOL lines.

Deliberately STATELESS: every method takes the current `lines` list. The
repair passes insert and delete lines, so a cached index would go stale
and silently address the wrong statement.
"""

from __future__ import annotations

from idms_db2_phase2.composers.cursor_close_guarantee.line_utils import (
    CursorGuaranteeLineUtils,
)
from idms_db2_phase2.composers.cursor_close_guarantee.models import (
    ParagraphHeader,
)
from patterns.cursor_close_guarantee_patterns import (
    PARAGRAPH_HEADER_PATTERN,
    SECTION_HEADER_PATTERN,
)
from rules.cursor_close_guarantee_rules import NON_PARAGRAPH_SINGLE_WORDS


class ParagraphIndex:
    """Finds paragraph headers and navigates between statements."""

    def __init__(
        self,
        line_utils: CursorGuaranteeLineUtils | None = None,
    ) -> None:
        self.lines_utils = line_utils or CursorGuaranteeLineUtils()

    #
    # Discovery
    #
    def headers(self, lines: list[str]) -> list[ParagraphHeader]:
        """Every real paragraph header, cursor paragraphs included.

        END-EXEC. and CONTINUE. look identical to a paragraph header at
        the token level, so NON_PARAGRAPH_SINGLE_WORDS filters them out.
        Treating one as a header would truncate the paragraph body at the
        first EXEC SQL block.
        """
        output: list[ParagraphHeader] = []

        for index, line in enumerate(lines):
            logical = self.lines_utils.logical(line)

            if not logical or self.lines_utils.is_comment(logical):
                continue

            if SECTION_HEADER_PATTERN.match(logical):
                continue

            match = PARAGRAPH_HEADER_PATTERN.match(logical)

            if not match:
                continue

            name = match.group("name").upper()

            if name in NON_PARAGRAPH_SINGLE_WORDS:
                continue

            output.append(ParagraphHeader(index=index, name=name))

        return output

    #
    # Navigation
    #
    @staticmethod
    def owner_paragraph(
        headers: list[ParagraphHeader],
        index: int,
    ) -> str:
        """Name of the paragraph that physically contains a line index."""
        owner = ""

        for header in headers:
            if header.index >= index:
                break
            owner = header.name

        return owner

    @staticmethod
    def span(
        headers: list[ParagraphHeader],
        name: str,
        total: int,
    ) -> tuple[int, int] | None:
        """(first body line, first line after the paragraph)."""
        target = str(name or "").upper()

        if not target:
            return None

        for position, header in enumerate(headers):
            if header.name != target:
                continue

            start = header.index + 1
            end = (
                headers[position + 1].index
                if position + 1 < len(headers)
                else total
            )
            return start, min(end, total)

        return None

    def exists(self, headers: list[ParagraphHeader], name: str) -> bool:
        target = str(name or "").upper()
        return any(header.name == target for header in headers)

    #
    # Statement stepping
    #
    def next_executable_index(
        self,
        lines: list[str],
        start: int,
        end: int,
    ) -> int:
        for index in range(max(0, start), min(end, len(lines))):
            if self.lines_utils.is_blank_or_comment(lines[index]):
                continue
            return index

        return -1

    def previous_executable_index(
        self,
        lines: list[str],
        start: int,
    ) -> int:
        """Previous statement, refusing to cross a paragraph boundary."""
        if not lines:
            return -1

        for index in range(min(start, len(lines) - 1), -1, -1):
            logical = self.lines_utils.logical(lines[index])

            if not logical or self.lines_utils.is_comment(logical):
                continue

            if PARAGRAPH_HEADER_PATTERN.match(logical):
                return -1

            return index

        return -1


__all__ = ["ParagraphIndex"]