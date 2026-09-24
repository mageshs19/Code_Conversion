# LOCATION: src/idms_db2_phase2/composers/cursor_flow/span_loop_rewriter.py
# ACTION: CREATE NEW FILE
"""Conservative rewrite for a SPAN driving loop.

Does exactly two things:

1. replaces the legacy exit condition with the cursor end-of-cursor flag,
2. guarantees the cursor CLOSE paragraph is performed after the loop.

It NEVER restructures the loop, never moves the business paragraph and
never deletes the in-loop FETCH. Restructuring a working span loop would
violate the business-flow preservation rule.
"""

from __future__ import annotations

from idms_db2_phase2.composers.cursor_flow.span_loop_plan import SpanLoopPlan
from idms_db2_phase2.composers.cursor_flow_line_formatter import (
    CursorFlowLineFormatter,
)
from patterns.cursor_loop_patterns import (
    PERFORM_CURSOR_PARAGRAPH_PATTERN,
    UNTIL_LINE_PATTERN,
)
from rules.cursor_loop_rules import (
    CLOSE_PRESENCE_WINDOW,
    CURSOR_LOOP_MESSAGES,
    PERFORM_CLOSE_TEMPLATE,
    STATEMENT_TERMINATOR,
    UNTIL_TEMPLATE,
    UNTIL_TERMINATED_TEMPLATE,
)


class SpanLoopRewriter:
    def __init__(
        self,
        line_formatter: CursorFlowLineFormatter | None = None,
    ) -> None:
        self.line_formatter = line_formatter or CursorFlowLineFormatter()
        self.messages: list[str] = []

    # ---------------------------------------------------------- public
    def rewrite(
        self,
        lines: list[str],
        plans: list[SpanLoopPlan],
    ) -> list[str]:
        self.messages = []

        if not plans:
            return lines

        output = list(lines)

        # Descending order so earlier indexes stay valid after insertion.
        for plan in sorted(
            plans,
            key=lambda item: item.loop.end_index,
            reverse=True,
        ):
            output = self._rewrite_condition(output, plan)
            output = self._ensure_close(output, plan)

        return output

    # ------------------------------------------------------ condition
    def _rewrite_condition(
        self,
        lines: list[str],
        plan: SpanLoopPlan,
    ) -> list[str]:
        loop = plan.loop
        if loop is None or not loop.condition_is_legacy:
            return lines

        index = loop.until_index
        if not 0 <= index < len(lines):
            return lines

        logical = self.line_formatter.logical(lines[index])

        if UNTIL_LINE_PATTERN.match(logical):
            template = (
                UNTIL_TERMINATED_TEMPLATE if loop.terminated
                else UNTIL_TEMPLATE
            )
            body = template.format(condition=plan.eoc_condition)
        else:
            # UNTIL is part of the PERFORM line - replace the tail only.
            head, _separator, _tail = logical.upper().partition("UNTIL")
            body = (
                f"{logical[:len(head)].rstrip()} "
                f"{UNTIL_TEMPLATE.format(condition=plan.eoc_condition)}"
            )
            if loop.terminated:
                body = f"{body}{STATEMENT_TERMINATOR}"

        lines[index] = self.line_formatter.format_like_line(
            reference_line=lines[index],
            replacement_body=body,
        )
        self._log("condition_rewritten", condition=plan.eoc_condition)
        return lines

    # ---------------------------------------------------------- close
    def _ensure_close(
        self,
        lines: list[str],
        plan: SpanLoopPlan,
    ) -> list[str]:
        if self._close_already_performed(lines, plan):
            self._log("close_present", paragraph=plan.close_paragraph)
            return lines

        insert_at = plan.loop.end_index + 1
        if insert_at > len(lines):
            insert_at = len(lines)

        reference = lines[plan.loop.end_index]
        close_line = self.line_formatter.format_like_line(
            reference_line=reference,
            replacement_body=PERFORM_CLOSE_TEMPLATE.format(
                paragraph=plan.close_paragraph,
            ),
        )

        lines.insert(insert_at, close_line)
        self._log("close_inserted", paragraph=plan.close_paragraph)
        return lines

    def _close_already_performed(
        self,
        lines: list[str],
        plan: SpanLoopPlan,
    ) -> bool:
        wanted = plan.close_paragraph.upper()

        start = max(0, plan.loop.end_index - CLOSE_PRESENCE_WINDOW)
        end = min(len(lines), plan.loop.end_index + CLOSE_PRESENCE_WINDOW)

        for index in range(start, end):
            logical = self.line_formatter.logical(lines[index])
            match = PERFORM_CURSOR_PARAGRAPH_PATTERN.match(logical)
            if not match:
                continue
            if match.group("operation").upper() != "CLOSE":
                continue
            name = (
                f"{int(match.group('number')):03d}-CLOSE-"
                f"{match.group('cursor').upper()}"
            )
            if name == wanted:
                return True

        return False

    # -------------------------------------------------------- helpers
    def _log(self, key: str, **values) -> None:
        template = CURSOR_LOOP_MESSAGES.get(key, "")
        if template:
            self.messages.append(template.format(**values))


__all__ = ["SpanLoopRewriter"]