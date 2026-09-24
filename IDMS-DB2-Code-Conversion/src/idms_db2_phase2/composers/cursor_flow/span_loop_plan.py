# LOCATION: src/idms_db2_phase2/composers/cursor_flow/span_loop_plan.py
# ACTION: CREATE NEW FILE
"""Correlates a generated cursor with a SPAN driving loop.

Search is whole-program and bidirectional: a span loop legitimately
precedes the paragraph that opens the cursor.
"""

from __future__ import annotations

from dataclasses import dataclass

from idms_db2_phase2.composers.cursor_flow.loop_shape import (
    LoopShape,
    LoopShapeScanner,
)
from idms_db2_phase2.composers.cursor_flow_line_formatter import (
    CursorFlowLineFormatter,
)
from patterns.cursor_loop_patterns import PERFORM_CURSOR_PARAGRAPH_PATTERN
from rules.cursor_loop_rules import (
    CURSOR_LOOP_MESSAGES,
    EOC_CONDITION_TEMPLATE,
    MAX_CORRELATION_DISTANCE,
)

FETCH_OFFSET = 10
CLOSE_OFFSET = 20


@dataclass
class SpanLoopPlan:
    """A cursor whose driving loop is a paragraph span."""

    cursor_name: str = ""
    open_index: int = -1
    open_number: int = 0
    fetch_paragraph: str = ""
    close_paragraph: str = ""
    eoc_condition: str = ""
    loop: LoopShape | None = None

    @property
    def is_usable(self) -> bool:
        return bool(
            self.cursor_name
            and self.close_paragraph
            and self.loop is not None
            and self.loop.has_condition
        )


class SpanLoopPlanBuilder:
    """Builds SpanLoopPlan values from scanned loop shapes."""

    def __init__(
        self,
        line_formatter: CursorFlowLineFormatter | None = None,
        scanner: LoopShapeScanner | None = None,
    ) -> None:
        self.line_formatter = line_formatter or CursorFlowLineFormatter()
        self.scanner = scanner or LoopShapeScanner(self.line_formatter)
        self.messages: list[str] = []

    # ---------------------------------------------------------- public
    def build(
        self,
        lines: list[str],
        shapes: list[LoopShape],
        claimed_cursors: set[str] | None = None,
    ) -> list[SpanLoopPlan]:
        """Plans for cursors NOT already handled by the inline strategy."""
        self.messages = []

        span_loops = self.scanner.span_loops(shapes)
        if not span_loops:
            return []

        already = {str(name).upper() for name in (claimed_cursors or set())}
        plans: list[SpanLoopPlan] = []
        used_loops: set[int] = set()

        for cursor, open_index, open_number in self._cursor_opens(lines):
            if cursor in already:
                continue

            loop = self._nearest_loop(span_loops, open_index, used_loops)
            if loop is None:
                self._log("no_loop_for_cursor", cursor=cursor)
                continue

            used_loops.add(loop.perform_index)

            plan = SpanLoopPlan(
                cursor_name=cursor,
                open_index=open_index,
                open_number=open_number,
                fetch_paragraph=(
                    f"{open_number + FETCH_OFFSET:03d}-FETCH-{cursor}"
                ),
                close_paragraph=(
                    f"{open_number + CLOSE_OFFSET:03d}-CLOSE-{cursor}"
                ),
                eoc_condition=EOC_CONDITION_TEMPLATE.format(cursor=cursor),
                loop=loop,
            )

            if not plan.is_usable:
                continue

            plans.append(plan)
            self._log(
                "span_plan",
                cursor=cursor,
                paragraph=loop.paragraph,
                through=loop.through,
            )

        return plans

    # -------------------------------------------------------- helpers
    def _cursor_opens(self, lines: list[str]):
        """(cursor, index, number) for every PERFORM nnn-OPEN-<cursor>."""
        seen: set[str] = set()

        for index, line in enumerate(lines):
            logical = self.line_formatter.logical(line)
            match = PERFORM_CURSOR_PARAGRAPH_PATTERN.match(logical)

            if not match:
                continue
            if match.group("operation").upper() != "OPEN":
                continue

            cursor = match.group("cursor").upper()
            if cursor in seen:
                continue

            seen.add(cursor)
            yield cursor, index, int(match.group("number"))

    @staticmethod
    def _nearest_loop(
        span_loops: list[LoopShape],
        open_index: int,
        used_loops: set[int],
    ) -> LoopShape | None:
        """Closest unused span loop, searched in BOTH directions.

        A loop still carrying the legacy end test is always preferred: it
        is the one that has not been converted yet.
        """
        candidates = [
            loop for loop in span_loops
            if loop.perform_index not in used_loops and loop.has_condition
        ]
        if not candidates:
            return None

        legacy = [loop for loop in candidates if loop.condition_is_legacy]
        pool = legacy or candidates

        if MAX_CORRELATION_DISTANCE > 0:
            pool = [
                loop for loop in pool
                if abs(loop.perform_index - open_index)
                <= MAX_CORRELATION_DISTANCE
            ]
            if not pool:
                return None

        return min(pool, key=lambda loop: abs(loop.perform_index - open_index))

    def _log(self, key: str, **values) -> None:
        template = CURSOR_LOOP_MESSAGES.get(key, "")
        if template:
            self.messages.append(template.format(**values))


__all__ = ["SpanLoopPlan", "SpanLoopPlanBuilder"]