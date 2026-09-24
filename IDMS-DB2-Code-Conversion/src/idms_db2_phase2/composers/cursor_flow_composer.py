# LOCATION: src/idms_db2_phase2/composers/cursor_flow_composer.py
# ACTION: REPLACE ENTIRE FILE
"""Cursor flow composer.

Two strategies, selected by the shape of the driving loop.

INLINE (unchanged, proven)
--------------------------
    PERFORM 710-OPEN-CURSOR.            PERFORM 710-OPEN-CURSOR.
    PERFORM 720-FETCH-CURSOR.     ->    PERFORM 720-FETCH-CURSOR
    PERFORM BUSINESS-PARA                   UNTIL CURSOR-EOC.
        UNTIL SQLCODE = 100.            PERFORM 730-CLOSE-CURSOR.

SPAN (older and LRF programs)
-----------------------------
    PERFORM BEHANDELING THRU BEHANDELING-EXIT
        UNTIL SQLCODE = 100.        ->      UNTIL DZBFASC1-EOC.
                                        PERFORM 730-CLOSE-DZBFASC1.

CORRECTION 1 - ungated OBTAIN NEXT cleanup
------------------------------------------
remove_leftover_obtain_next_cursor_calls() previously ran even when NO
plan had been produced, deleting the only FETCH inside the loop.

CORRECTION 2 - SPAN must not authorise the cleanup
--------------------------------------------------
The first gate accepted ANY plan, including a SPAN plan. A SPAN rewrite
keeps the loop body untouched and never emits PERFORM <fetch> UNTIL
<eoc>, so its in-loop fetch is REQUIRED. Gating on a SPAN plan therefore
reproduced the original defect: the loop ran forever because SQLCODE
never changed. Only an INLINE rewrite authorises the cleanup.

Orchestration only. Regex lives in patterns/, constants in rules/.
"""

from __future__ import annotations

from idms_db2_phase2.composers.cursor_flow.loop_shape import LoopShapeScanner
from idms_db2_phase2.composers.cursor_flow.span_loop_plan import (
    SpanLoopPlanBuilder,
)
from idms_db2_phase2.composers.cursor_flow.span_loop_rewriter import (
    SpanLoopRewriter,
)
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
from rules.cursor_loop_rules import (
    CURSOR_LOOP_MESSAGES,
    ENFORCE_SPAN_LOOP_REWRITE,
    REQUIRE_PLAN_FOR_OBTAIN_NEXT_CLEANUP,
)


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
        self.loop_scanner = LoopShapeScanner(
            line_formatter=self.line_formatter,
        )
        self.span_plan_builder = SpanLoopPlanBuilder(
            line_formatter=self.line_formatter,
            scanner=self.loop_scanner,
        )
        self.span_rewriter = SpanLoopRewriter(
            line_formatter=self.line_formatter,
        )
        self.messages: list[str] = []

    # ---------------------------------------------------------- public
    def compose(self, text: str) -> str:
        self.messages = []

        if not text:
            return ""

        lines = self.line_formatter.normalize_line_endings(text).splitlines()

        # ---- Strategy 1: INLINE (unchanged behaviour)
        plans = self.plan_discoverer.discover(lines)

        # Only an INLINE rewrite replaces the loop with
        # PERFORM <fetch> UNTIL <eoc>. Nothing else may authorise the
        # OBTAIN NEXT cleanup.
        converted_inline = bool(plans)

        if plans:
            lines = self.rewriter.rewrite_main_flow(lines=lines, plans=plans)
            lines = self.rewriter.rewrite_fetch_paragraphs(
                lines=lines,
                plans=plans,
            )

        # ---- Strategy 2: SPAN
        if ENFORCE_SPAN_LOOP_REWRITE:
            shapes = self.loop_scanner.scan(lines)
            self._log(
                "scanned",
                inline=len(self.loop_scanner.inline_loops(shapes)),
                span=len(self.loop_scanner.span_loops(shapes)),
            )
            span_plans = self.span_plan_builder.build(
                lines=lines,
                shapes=shapes,
                claimed_cursors={plan.cursor_name for plan in plans},
            )
            self.messages.extend(self.span_plan_builder.messages)

            if span_plans:
                lines = self.span_rewriter.rewrite(
                    lines=lines,
                    plans=span_plans,
                )
                self.messages.extend(self.span_rewriter.messages)
                # DELIBERATELY does not set converted_inline: the span
                # loop still needs its own in-loop fetch.

        # ---- Cleanup: only after an INLINE conversion
        if converted_inline or not REQUIRE_PLAN_FOR_OBTAIN_NEXT_CLEANUP:
            lines = (
                self.obtain_next_cleanup
                .remove_leftover_obtain_next_cursor_calls(lines)
            )
        else:
            self._log("obtain_next_retained")

        return "\n".join(lines).rstrip() + "\n"

    # -------------------------------------------------------- helpers
    def _log(self, key: str, **values) -> None:
        template = CURSOR_LOOP_MESSAGES.get(key, "")
        if template:
            self.messages.append(template.format(**values))


__all__ = ["CursorFlowComposer"]