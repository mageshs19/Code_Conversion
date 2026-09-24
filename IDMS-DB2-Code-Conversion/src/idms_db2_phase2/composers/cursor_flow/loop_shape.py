# LOCATION: src/idms_db2_phase2/composers/cursor_flow/loop_shape.py
# ACTION: CREATE NEW FILE
"""Classifies every driving loop in a program, whatever the idiom.

Read-only. Produces LoopShape values; rewrites nothing.
"""

from __future__ import annotations

from dataclasses import dataclass

from idms_db2_phase2.composers.cursor_flow_line_formatter import (
    CursorFlowLineFormatter,
)
from patterns.cursor_loop_patterns import (
    PERFORM_CURSOR_PARAGRAPH_PATTERN,
    PERFORM_INLINE_WITH_UNTIL_PATTERN,
    PERFORM_SIMPLE_PATTERN,
    PERFORM_SPAN_PATTERN,
    PERFORM_SPAN_WITH_UNTIL_PATTERN,
    UNTIL_LINE_PATTERN,
)
from rules.cursor_loop_rules import (
    LEGACY_EOC_CONDITIONS,
    LOOP_KIND_INLINE,
    LOOP_KIND_SPAN,
)

UNTIL_CONTINUATION_WINDOW = 4
COMMENT_PREFIXES = ("*", "/")


@dataclass
class LoopShape:
    """One driving loop, normalised across idioms."""

    kind: str = ""
    paragraph: str = ""
    through: str = ""
    condition: str = ""
    perform_index: int = -1
    until_index: int = -1
    end_index: int = -1
    terminated: bool = False

    @property
    def is_span(self) -> bool:
        return self.kind == LOOP_KIND_SPAN

    @property
    def has_condition(self) -> bool:
        return bool(self.condition)

    @property
    def condition_is_legacy(self) -> bool:
        probe = self.condition.upper().replace(" ", "")
        return any(
            legacy.replace(" ", "") in probe
            for legacy in LEGACY_EOC_CONDITIONS
        )


class LoopShapeScanner:
    """Finds every driving loop, in both idioms, anywhere in the program."""

    def __init__(
        self,
        line_formatter: CursorFlowLineFormatter | None = None,
    ) -> None:
        self.line_formatter = line_formatter or CursorFlowLineFormatter()

    # ---------------------------------------------------------- public
    def scan(self, lines: list[str]) -> list[LoopShape]:
        shapes: list[LoopShape] = []
        index = 0

        while index < len(lines):
            logical = self._logical(lines[index])

            if not logical or self._is_comment(logical):
                index += 1
                continue

            # A generated cursor PERFORM is never a business driving loop.
            if PERFORM_CURSOR_PARAGRAPH_PATTERN.match(logical):
                index += 1
                continue

            shape = self._shape_at(lines, index, logical)
            if shape is None:
                index += 1
                continue

            shapes.append(shape)
            index = shape.end_index + 1

        return shapes

    @staticmethod
    def inline_loops(shapes: list[LoopShape]) -> list[LoopShape]:
        return [s for s in shapes if s.kind == LOOP_KIND_INLINE]

    @staticmethod
    def span_loops(shapes: list[LoopShape]) -> list[LoopShape]:
        return [s for s in shapes if s.kind == LOOP_KIND_SPAN]

    # --------------------------------------------------------- shapes
    def _shape_at(
        self,
        lines: list[str],
        index: int,
        logical: str,
    ) -> LoopShape | None:
        # 1. PERFORM a THRU b UNTIL cond.
        match = PERFORM_SPAN_WITH_UNTIL_PATTERN.match(logical)
        if match:
            return LoopShape(
                kind=LOOP_KIND_SPAN,
                paragraph=match.group("paragraph").upper(),
                through=match.group("through").upper(),
                condition=match.group("condition").strip(),
                perform_index=index,
                until_index=index,
                end_index=index,
                terminated=logical.rstrip().endswith("."),
            )

        # 2. PERFORM a THRU b  /  UNTIL cond.
        match = PERFORM_SPAN_PATTERN.match(logical)
        if match:
            until_index, condition, terminated = self._until_after(
                lines, index + 1
            )
            return LoopShape(
                kind=LOOP_KIND_SPAN,
                paragraph=match.group("paragraph").upper(),
                through=match.group("through").upper(),
                condition=condition,
                perform_index=index,
                until_index=until_index if until_index >= 0 else index,
                end_index=until_index if until_index >= 0 else index,
                terminated=terminated,
            )

        # 3. PERFORM a UNTIL cond.
        match = PERFORM_INLINE_WITH_UNTIL_PATTERN.match(logical)
        if match:
            return LoopShape(
                kind=LOOP_KIND_INLINE,
                paragraph=match.group("paragraph").upper(),
                condition=match.group("condition").strip(),
                perform_index=index,
                until_index=index,
                end_index=index,
                terminated=logical.rstrip().endswith("."),
            )

        # 4. PERFORM a  /  UNTIL cond.
        match = PERFORM_SIMPLE_PATTERN.match(logical)
        if match:
            until_index, condition, terminated = self._until_after(
                lines, index + 1
            )
            if until_index < 0:
                return None
            return LoopShape(
                kind=LOOP_KIND_INLINE,
                paragraph=match.group("paragraph").upper(),
                condition=condition,
                perform_index=index,
                until_index=until_index,
                end_index=until_index,
                terminated=terminated,
            )

        return None

    def _until_after(
        self,
        lines: list[str],
        start_index: int,
    ) -> tuple[int, str, bool]:
        end = min(len(lines), start_index + UNTIL_CONTINUATION_WINDOW)

        for index in range(start_index, end):
            logical = self._logical(lines[index])
            if not logical or self._is_comment(logical):
                continue

            match = UNTIL_LINE_PATTERN.match(logical)
            if match:
                return (
                    index,
                    match.group("condition").strip(),
                    bool(match.group("terminator")),
                )
            break

        return -1, "", False

    # -------------------------------------------------------- helpers
    def _logical(self, line: str) -> str:
        return self.line_formatter.logical(line)

    @staticmethod
    def _is_comment(logical: str) -> bool:
        return logical.startswith(COMMENT_PREFIXES)


__all__ = ["LoopShape", "LoopShapeScanner"]