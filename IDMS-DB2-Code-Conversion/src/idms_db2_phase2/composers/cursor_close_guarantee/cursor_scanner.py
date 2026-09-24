# LOCATION: src/idms_db2_phase2/composers/cursor_close_guarantee/cursor_scanner.py
# ACTION: CREATE NEW FILE

"""Read-only discovery of generated cursor paragraphs and their PERFORMs.

Knows how to recognise a generated cursor paragraph header and a PERFORM
of one. Knows nothing about loops, conditions or repairs.
"""

from __future__ import annotations

from idms_db2_phase2.composers.cursor_close_guarantee.line_utils import (
    CursorGuaranteeLineUtils,
)
from idms_db2_phase2.composers.cursor_close_guarantee.models import (
    CursorParagraphSet,
    CursorPerform,
)
from patterns.cursor_close_guarantee_patterns import (
    CURSOR_PARAGRAPH_HEADER_PATTERN,
    PERFORM_CURSOR_PARAGRAPH_PATTERN,
)

PARAGRAPH_NAME_TEMPLATE = "{number:03d}-{operation}-{cursor}"


class CursorScanner:
    """Finds generated cursor paragraphs and every PERFORM of them."""

    def __init__(
        self,
        line_utils: CursorGuaranteeLineUtils | None = None,
    ) -> None:
        self.lines_utils = line_utils or CursorGuaranteeLineUtils()

    #
    # Paragraph headers
    #
    def paragraph_sets(self, lines: list[str]) -> dict:
        """Map every cursor to its generated OPEN / FETCH / CLOSE names."""
        found: dict = {}

        for line in lines:
            logical = self.lines_utils.logical(line)

            if not logical:
                continue

            match = CURSOR_PARAGRAPH_HEADER_PATTERN.match(logical)

            if not match:
                continue

            cursor = match.group("cursor").upper()
            operation = match.group("operation").upper()
            name = PARAGRAPH_NAME_TEMPLATE.format(
                number=int(match.group("number")),
                operation=operation,
                cursor=cursor,
            )

            entry = found.setdefault(
                cursor,
                CursorParagraphSet(cursor=cursor, names={}),
            )
            entry.remember(operation, name)

        return found

    #
    # PERFORM statements
    #
    def performs(
        self,
        lines: list[str],
        cursor: str,
    ) -> list[CursorPerform]:
        """Every PERFORM of a generated paragraph belonging to one cursor."""
        target = str(cursor or "").upper()
        output: list[CursorPerform] = []

        if not target:
            return output

        for index, line in enumerate(lines):
            logical = self.lines_utils.logical(line)

            if not logical or self.lines_utils.is_comment(logical):
                continue

            match = PERFORM_CURSOR_PARAGRAPH_PATTERN.match(logical)

            if not match:
                continue

            if match.group("cursor").upper() != target:
                continue

            operation = match.group("operation").upper()

            output.append(
                CursorPerform(
                    index=index,
                    operation=operation,
                    paragraph=PARAGRAPH_NAME_TEMPLATE.format(
                        number=int(match.group("number")),
                        operation=operation,
                        cursor=target,
                    ),
                    tail=str(match.group("tail") or "").strip(),
                )
            )

        return output

    @staticmethod
    def by_operation(
        performs: list[CursorPerform],
        operation: str,
    ) -> list[CursorPerform]:
        return [p for p in performs if p.operation == operation]


__all__ = ["PARAGRAPH_NAME_TEMPLATE", "CursorScanner"]