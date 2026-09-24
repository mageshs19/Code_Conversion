# LOCATION: src/idms_db2_phase2/composers/cursor_close_guarantee/loop_finder.py
# ACTION: CREATE NEW FILE

"""Finds the business loop that drives a given paragraph.

Four idioms are recognised, in priority order:

    PERFORM <para> THRU <exit> UNTIL <cond>.
    PERFORM <para> UNTIL <cond>.
    PERFORM <para> THRU <exit>          + UNTIL on a later line
    PERFORM <para>                      + UNTIL on a later line

A PERFORM of a GENERATED cursor paragraph is never a business driving
loop and is skipped, otherwise the pass would correlate the cursor with
its own fetch call.
"""

from __future__ import annotations

from idms_db2_phase2.composers.cursor_close_guarantee.line_utils import (
    CursorGuaranteeLineUtils,
)
from idms_db2_phase2.composers.cursor_close_guarantee.models import LoopShape
from patterns.cursor_close_guarantee_patterns import (
    PERFORM_CURSOR_PARAGRAPH_PATTERN,
    PERFORM_INLINE_WITH_UNTIL_PATTERN,
    PERFORM_PARAGRAPH_PATTERN,
    PERFORM_SPAN_PATTERN,
    PERFORM_SPAN_WITH_UNTIL_PATTERN,
    UNTIL_ONLY_PATTERN,
)
from rules.cursor_close_guarantee_rules import UNTIL_LOOKAHEAD_LIMIT

SAME_LINE_PATTERNS = (
    PERFORM_SPAN_WITH_UNTIL_PATTERN,
    PERFORM_INLINE_WITH_UNTIL_PATTERN,
)

LOOKAHEAD_PATTERNS = (
    PERFORM_SPAN_PATTERN,
    PERFORM_PARAGRAPH_PATTERN,
)


class BusinessLoopFinder:
    """Locates the driving loop of a business paragraph, if one exists."""

    def __init__(
        self,
        line_utils: CursorGuaranteeLineUtils | None = None,
    ) -> None:
        self.lines_utils = line_utils or CursorGuaranteeLineUtils()

    #
    # Public entry point
    #
    def find(
        self,
        lines: list[str],
        business: str,
    ) -> LoopShape | None:
        target = str(business or "").upper()

        if not target:
            return None

        for index, line in enumerate(lines):
            logical = self.lines_utils.logical(line)

            if not logical or self.lines_utils.is_comment(logical):
                continue

            # A generated cursor PERFORM is never a business driving loop.
            if PERFORM_CURSOR_PARAGRAPH_PATTERN.match(logical):
                continue

            shape = self._same_line_loop(logical, index, target)

            if shape is not None:
                return shape

            shape = self._lookahead_loop(lines, logical, index, target)

            if shape is not None:
                return shape

        return None

    #
    # Idiom handlers
    #
    def _same_line_loop(
        self,
        logical: str,
        index: int,
        target: str,
    ) -> LoopShape | None:
        """PERFORM ... UNTIL <cond> all on one line."""
        for pattern in SAME_LINE_PATTERNS:
            match = pattern.match(logical)

            if not match:
                continue

            if match.group("paragraph").upper() != target:
                continue

            return LoopShape(
                perform_index=index,
                until_index=index,
                end_index=index,
                condition=match.group("condition").strip(),
                terminated=self.lines_utils.is_terminated(logical),
            )

        return None

    def _lookahead_loop(
        self,
        lines: list[str],
        logical: str,
        index: int,
        target: str,
    ) -> LoopShape | None:
        """PERFORM ... with the UNTIL clause on a continuation line."""
        for pattern in LOOKAHEAD_PATTERNS:
            match = pattern.match(logical)

            if not match:
                continue

            if match.group("paragraph").upper() != target:
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
                    terminated=self.lines_utils.is_terminated(logical),
                )

            index += 1

        return None


__all__ = ["BusinessLoopFinder"]