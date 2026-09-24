# LOCATION: src/idms_db2_phase2/composers/cursor_guarantee/cursor_scanner.py
# ACTION: CREATE NEW FILE

"""Read-only discovery over generated COBOL.

Finds generated cursor paragraphs, every PERFORM of them, and the
business driving loop - if one exists. Rewrites nothing, inserts
nothing, deletes nothing: every mutation lives in cursor_repair.py.
"""

from __future__ import annotations

from idms_db2_phase2.composers.cursor_guarantee.cursor_lines import CursorLines
from idms_db2_phase2.composers.cursor_guarantee.cursor_models import (
    CURSOR_PARAGRAPH_HEADER_PATTERN,
    PARAGRAPH_NAME_TEMPLATE,
    PERFORM_CURSOR_PARAGRAPH_PATTERN,
    PERFORM_INLINE_WITH_UNTIL_PATTERN,
    PERFORM_PARAGRAPH_PATTERN,
    PERFORM_SPAN_PATTERN,
    PERFORM_SPAN_WITH_UNTIL_PATTERN,
    UNTIL_ONLY_PATTERN,
    CursorParagraphSet,
    CursorPerform,
    LoopShape,
)
from rules.cursor_close_guarantee_rules import (
    STATEMENT_TERMINATOR,
    UNTIL_LOOKAHEAD_LIMIT,
)


class CursorScanner:
    """Everything this pass needs to KNOW before it changes anything."""

    def __init__(self, lines_utils: CursorLines | None = None) -> None:
        self.lines_utils = lines_utils or CursorLines()

    # =================================================================
    # Generated cursor paragraphs
    # =================================================================
    def paragraph_sets(self, lines: list[str]) -> dict:
        """Map every cursor to its OPEN / FETCH / CLOSE paragraph names."""
        found: dict = {}

        for line in lines:
            logical = self.lines_utils.logical(line)

            if not logical or self.lines_utils.is_comment(logical):
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
            entry.names.setdefault(operation, name)

        return found

    # =================================================================
    # PERFORM statements
    # =================================================================
    def performs(
        self,
        lines: list[str],
        cursor: str,
    ) -> list[CursorPerform]:
        """Every PERFORM of a generated paragraph of ONE cursor."""
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
        return [item for item in performs if item.operation == operation]

    # =================================================================
    # Business driving loop
    # =================================================================
    def find_business_loop(
        self,
        lines: list[str],
        business: str,
    ) -> LoopShape | None:
        """The loop that drives the business paragraph, if any."""
        target = str(business or "").upper()

        if not target:
            return None

        for index, line in enumerate(lines):
            logical = self.lines_utils.logical(line)

            if not logical or self.lines_utils.is_comment(logical):
                continue

            # A generated cursor PERFORM is never a business loop.
            if PERFORM_CURSOR_PARAGRAPH_PATTERN.match(logical):
                continue

            shape = self._one_line_loop(logical, index, target)
            if shape is not None:
                return shape

            shape = self._two_line_loop(lines, logical, index, target)
            if shape is not None:
                return shape

        return None

    def _one_line_loop(
        self,
        logical: str,
        index: int,
        target: str,
    ) -> LoopShape | None:
        """PERFORM ... [THRU ...] UNTIL <condition> on a single line."""
        for pattern in (
            PERFORM_SPAN_WITH_UNTIL_PATTERN,
            PERFORM_INLINE_WITH_UNTIL_PATTERN,
        ):
            match = pattern.match(logical)

            if not match or match.group("paragraph").upper() != target:
                continue

            return LoopShape(
                perform_index=index,
                until_index=index,
                end_index=index,
                condition=match.group("condition").strip(),
                terminated=logical.rstrip().endswith(STATEMENT_TERMINATOR),
            )

        return None

    def _two_line_loop(
        self,
        lines: list[str],
        logical: str,
        index: int,
        target: str,
    ) -> LoopShape | None:
        """PERFORM whose UNTIL clause sits on a continuation line."""
        for pattern in (PERFORM_SPAN_PATTERN, PERFORM_PARAGRAPH_PATTERN):
            match = pattern.match(logical)

            if not match or match.group("paragraph").upper() != target:
                continue

            return self._until_on_following_line(lines, index)

        return None

    def _until_on_following_line(
        self,
        lines: list[str],
        perform_index: int,
    ) -> LoopShape | None:
        scanned = 0
        index = perform_index + 1

        while index < len(lines) and scanned < UNTIL_LOOKAHEAD_LIMIT:
            logical = self.lines_utils.logical(lines[index])

            if not logical or self.lines_utils.is_comment(logical):
                index += 1
                continue

            scanned += 1
            match = UNTIL_ONLY_PATTERN.match(logical)

            if match:
                return LoopShape(
                    perform_index=perform_index,
                    until_index=index,
                    end_index=index,
                    condition=match.group("condition").strip(),
                    terminated=logical.rstrip().endswith(STATEMENT_TERMINATOR),
                )

            index += 1

        return None


__all__ = ["CursorScanner"]