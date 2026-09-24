# LOCATION: src/idms_db2_phase2/composers/cursor_guarantee/cursor_lines.py
# ACTION: CREATE NEW FILE

"""Logical-line access and paragraph navigation.

Deliberately STATELESS: every method takes the current `lines` list. The
repair passes insert and delete lines, so a cached index would go stale
and silently address the wrong statement.

Wraps CursorFlowLineFormatter so the whole package shares one definition
of "logical line" and one definition of "format like this reference
line". Owns no business decision.
"""

from __future__ import annotations

from idms_db2_phase2.composers.cursor_flow_line_formatter import (
    CursorFlowLineFormatter,
)
from idms_db2_phase2.composers.cursor_guarantee.cursor_models import (
    COMMENT_INDICATORS,
    PARAGRAPH_HEADER_PATTERN,
    SECTION_HEADER_PATTERN,
    UNTIL_KEYWORD,
    ParagraphHeader,
)
from rules.cursor_close_guarantee_rules import (
    LEGACY_EOC_CONDITIONS,
    NON_PARAGRAPH_SINGLE_WORDS,
)


class CursorLines:
    """Line inspection, line rewriting and paragraph navigation."""

    def __init__(
        self,
        line_formatter: CursorFlowLineFormatter | None = None,
    ) -> None:
        self.line_formatter = line_formatter or CursorFlowLineFormatter()

    # =================================================================
    # Text views
    # =================================================================
    def logical(self, line: str) -> str:
        """The COBOL body, sequence area and indicator removed.

        Never raises: one malformed line must not abort a whole pass.
        """
        try:
            return str(self.line_formatter.logical(line) or "").strip()
        except Exception:  # noqa: BLE001
            return str(line or "").strip()

    def format_like(self, reference_line: str, body: str) -> str:
        """Rebuild `body` inside the fixed-format frame of a real line."""
        return self.line_formatter.format_like_line(
            reference_line=reference_line,
            replacement_body=body,
        )

    @staticmethod
    def is_comment(logical: str) -> bool:
        text = str(logical or "").strip()
        return bool(text) and text[0] in COMMENT_INDICATORS

    @staticmethod
    def compress(text: str) -> str:
        """Whitespace-insensitive, case-insensitive comparison form."""
        return " ".join(str(text or "").split()).upper()

    @staticmethod
    def normalize_line_endings(text: str) -> str:
        return str(text or "").replace("\r\n", "\n").replace("\r", "\n")

    # =================================================================
    # Conditions
    # =================================================================
    @staticmethod
    def partition_until(logical: str) -> tuple[str, str, str]:
        """Split a logical line on UNTIL, preserving the original case."""
        text = str(logical or "")
        position = text.upper().find(UNTIL_KEYWORD)

        if position < 0:
            return text, "", ""

        head = text[:position]
        tail = text[position + len(UNTIL_KEYWORD) :].strip()

        return head, UNTIL_KEYWORD, tail

    def is_legacy_condition(self, condition: str) -> bool:
        """True for a raw SQLCODE / IDMS end test still in the loop."""
        current = self.compress(condition)

        if not current:
            return False

        return any(
            current == self.compress(candidate)
            for candidate in LEGACY_EOC_CONDITIONS
        )

    # =================================================================
    # Statement stepping
    # =================================================================
    def next_executable_index(
        self,
        lines: list[str],
        start: int,
        end: int,
    ) -> int:
        for index in range(max(0, start), min(end, len(lines))):
            logical = self.logical(lines[index])

            if not logical or self.is_comment(logical):
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
            logical = self.logical(lines[index])

            if not logical or self.is_comment(logical):
                continue

            if PARAGRAPH_HEADER_PATTERN.match(logical):
                return -1

            return index

        return -1

    # =================================================================
    # Paragraphs
    # =================================================================
    def paragraph_headers(self, lines: list[str]) -> list[ParagraphHeader]:
        """Every real paragraph header, cursor paragraphs included."""
        headers: list[ParagraphHeader] = []

        for index, line in enumerate(lines):
            logical = self.logical(line)

            if not logical or self.is_comment(logical):
                continue

            if SECTION_HEADER_PATTERN.match(logical):
                continue

            match = PARAGRAPH_HEADER_PATTERN.match(logical)

            if not match:
                continue

            name = match.group("name").upper()

            # EXIT. and END-IF. also end in a period but head nothing.
            if name in NON_PARAGRAPH_SINGLE_WORDS:
                continue

            headers.append(ParagraphHeader(index=index, name=name))

        return headers

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
    def paragraph_span(
        headers: list[ParagraphHeader],
        name: str,
        total: int,
    ) -> tuple[int, int] | None:
        """(first body line, first line after the paragraph)."""
        target = str(name or "").upper()

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


__all__ = ["CursorLines"]