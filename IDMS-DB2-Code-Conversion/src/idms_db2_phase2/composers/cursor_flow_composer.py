"""
Cursor flow composer.

Normalizes generated cursor execution flow.

It converts mechanical flow:

    PERFORM 710-OPEN-CURSOR.
    PERFORM 720-FETCH-CURSOR.
    PERFORM BUSINESS-PARA
      UNTIL SQLCODE = 100.

to:

    PERFORM 710-OPEN-CURSOR.
    PERFORM 720-FETCH-CURSOR UNTIL CURSOR-EOC.
    PERFORM 730-CLOSE-CURSOR.

It also converts generated FETCH paragraphs (WHEN ZERO / CONTINUE) into a
PERFORM of the business paragraph, and removes leftover generated OBTAIN
NEXT cursor calls after a cursor has been converted to FETCH UNTIL EOC.

This composer is generic. It does not hardcode program names, record names,
table names, cursor names, or business paragraph names. It owns no regex and
no constants; those live in patterns/cursor_flow_patterns.py and
rules/cursor_flow_rules.py. It only orchestrates helper classes.
"""

from idms_db2_phase2.composers.cursor_flow_line_formatter import (
    CursorFlowLineFormatter,
)
from idms_db2_phase2.composers.cursor_flow_obtain_next_cleanup import (
    CursorFlowObtainNextCleanup,
)
from idms_db2_phase2.composers.cursor_flow_plan_discoverer import (
    CursorFlowPlanDiscoverer,
)
from idms_db2_phase2.composers.cursor_flow_rewriter import CursorFlowRewriter


class CursorFlowComposer:
    def __init__(self) -> None:
        self.line_formatter = CursorFlowLineFormatter()
        self.plan_discoverer = CursorFlowPlanDiscoverer(
            line_formatter=self.line_formatter,
        )
        self.rewriter = CursorFlowRewriter(
            line_formatter=self.line_formatter,
        )
        self.obtain_next_cleanup = CursorFlowObtainNextCleanup(
            line_formatter=self.line_formatter,
        )

    def compose(self, text: str) -> str:
        if not text:
            return ""

        lines = self.line_formatter.normalize_line_endings(text).splitlines()

        plans = self.plan_discoverer.discover(lines)

        if plans:
            lines = self.rewriter.rewrite_main_flow(
                lines=lines,
                plans=plans,
            )
            lines = self.rewriter.rewrite_fetch_paragraphs(
                lines=lines,
                plans=plans,
            )

        lines = self.obtain_next_cleanup.remove_leftover_obtain_next_cursor_calls(
            lines
        )

        return "\n".join(lines).rstrip() + "\n"