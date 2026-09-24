# LOCATION: src/idms_db2_phase2/composers/cursor_close_guarantee_composer.py
# ACTION: REPLACE ENTIRE FILE

"""Guarantees that every generated cursor is looped and closed.

Runs AFTER CursorFlowComposer. A no-op for any cursor the INLINE or SPAN
strategy already handled, and a last-resort repair for every cursor they
could not correlate.

WHY THIS EXISTS
---------------
CursorFlowComposer recognises two driving-loop idioms. An LRF-expanded
program matches neither, so the program shipped as:

    PERFORM 710-OPEN-DZBFASC1.
    PERFORM 720-FETCH-DZBFASC1.        <- primes once, never loops
    ...
 BEHANDELING.
    PERFORM 720-FETCH-DZBFASC1.        <- orphan repeat fetch

with 730-CLOSE-DZBFASC1 declared but never performed and the FETCH
paragraph carrying WHEN ZERO / CONTINUE. The cursor is opened, read
twice, leaked, and no fetched row is ever processed. Required shape:

    PERFORM 710-OPEN-DZBFASC1.
    PERFORM 720-FETCH-DZBFASC1 UNTIL DZBFASC1-EOC.
    PERFORM 730-CLOSE-DZBFASC1.

with the FETCH paragraph driving the business paragraph:

    EVALUATE SQLCODE
      WHEN ZERO
           PERFORM BEHANDELING THRU BEHANDELING-EXIT

THREE REPAIR PATHS
------------------
A. A fetch PERFORM already carries UNTIL -> INLINE already ran.
   Normalise a legacy exit condition and guarantee the CLOSE.

B. A business loop drives the paragraph that held the OBTAIN NEXT
   -> SPAN shape. Normalise its exit condition and guarantee the CLOSE.
   The in-loop fetch is REQUIRED here and is never removed.

C. No loop at all -> synthesise the shape, bind the FETCH paragraph to
   the business paragraph, and remove the orphan repeat fetch.

RESPONSIBILITY
--------------
This class owns PATH SELECTION and nothing else:

    cursor_guarantee/cursor_models.py    regex, value objects, log
    cursor_guarantee/cursor_lines.py     logical lines, paragraphs
    cursor_guarantee/cursor_scanner.py   discovery, read-only
    cursor_guarantee/cursor_repair.py    every mutation

Concrete module imports, not the package: a stale or partially updated
__init__.py then cannot break this composer, which is precisely the
failure mode that produced

    ImportError: cannot import name 'CONTINUE_PATTERN' from partially
    initialized module 'patterns.cursor_close_guarantee_patterns'

No program, paragraph, record, table, cursor or host variable name is
hardcoded here.
"""

from __future__ import annotations

from idms_db2_phase2.composers.cursor_flow_line_formatter import (
    CursorFlowLineFormatter,
)
from idms_db2_phase2.composers.cursor_guarantee.cursor_lines import CursorLines
from idms_db2_phase2.composers.cursor_guarantee.cursor_models import (
    CursorParagraphSet,
    CursorPerform,
    MessageLog,
)
from idms_db2_phase2.composers.cursor_guarantee.cursor_repair import CursorRepair
from idms_db2_phase2.composers.cursor_guarantee.cursor_scanner import (
    CursorScanner,
)
from rules.cursor_close_guarantee_rules import (
    ENFORCE_CURSOR_CLOSE_GUARANTEE,
    EOC_CONDITION_TEMPLATE,
    OPERATION_CLOSE,
    OPERATION_FETCH,
    OPERATION_OPEN,
    SYNTHESISE_MISSING_DRIVING_LOOP,
)


class CursorCloseGuaranteeComposer:
    """Last-resort guarantee that a generated cursor loops and closes."""

    def __init__(
        self,
        line_formatter: CursorFlowLineFormatter | None = None,
    ) -> None:
        self.log = MessageLog()
        self.lines_utils = CursorLines(line_formatter=line_formatter)
        self.scanner = CursorScanner(lines_utils=self.lines_utils)
        self.repair = CursorRepair(
            lines_utils=self.lines_utils,
            log=self.log,
        )

    #
    # conversion_pipeline drains this after compose()
    #
    @property
    def messages(self) -> list[str]:
        return self.log.messages

    # =================================================================
    # Public entry point
    # =================================================================
    def compose(self, text: str) -> str:
        self.log.reset()

        if not text:
            return ""

        if not ENFORCE_CURSOR_CLOSE_GUARANTEE:
            return str(text)

        lines = self.lines_utils.normalize_line_endings(text).splitlines()

        if not lines:
            return ""

        cursor_sets = self.scanner.paragraph_sets(lines)

        # A program with no generated cursor is a legitimate outcome, but
        # it must be distinguishable from a pass that did not run at all.
        if not cursor_sets:
            self.log.log("no_cursor_paragraphs")
            return "\n".join(lines).rstrip() + "\n"

        for cursor in sorted(cursor_sets):
            cursor_set = cursor_sets[cursor]

            if not cursor_set.is_complete:
                self.log.log("incomplete_paragraph_set", cursor=cursor)
                continue

            lines = self._repair_cursor(lines, cursor_set)

        return "\n".join(lines).rstrip() + "\n"

    # =================================================================
    # Path selection
    # =================================================================
    def _repair_cursor(
        self,
        lines: list[str],
        cursor_set: CursorParagraphSet,
    ) -> list[str]:
        cursor = cursor_set.cursor
        eoc_condition = EOC_CONDITION_TEMPLATE.format(cursor=cursor)

        performs = self.scanner.performs(lines, cursor)
        opens = self.scanner.by_operation(performs, OPERATION_OPEN)
        fetches = self.scanner.by_operation(performs, OPERATION_FETCH)
        closes = self.scanner.by_operation(performs, OPERATION_CLOSE)

        # A declared but never opened cursor is dead code, not a broken
        # loop. Repairing it would invent a flow the program never had.
        if not opens:
            self.log.log("no_open_perform", cursor=cursor)
            return lines

        # ---- Path A: an INLINE loop already exists.
        driving = next((item for item in fetches if item.has_until), None)

        if driving is not None:
            return self._repair_inline(
                lines=lines,
                cursor_set=cursor_set,
                driving=driving,
                closes=closes,
                eoc_condition=eoc_condition,
            )

        # An opened cursor with no fetch at all cannot be repaired here:
        # there is no statement to turn into the driving loop.
        if not fetches:
            self.log.log("no_fetch_perform", cursor=cursor)
            return lines

        priming = fetches[0]
        repeats = fetches[1:]
        business = self._business_paragraph(lines, repeats)

        # ---- Path B: a business loop already drives that paragraph.
        loop = (
            self.scanner.find_business_loop(lines, business)
            if business
            else None
        )

        if loop is not None:
            return self._repair_span(
                lines=lines,
                cursor_set=cursor_set,
                loop=loop,
                closes=closes,
                eoc_condition=eoc_condition,
            )

        # ---- Path C: nothing drives the cursor.
        if not SYNTHESISE_MISSING_DRIVING_LOOP:
            self.log.log("synthesis_disabled", cursor=cursor)
            return lines

        return self.repair.synthesise_loop(
            lines=lines,
            cursor_set=cursor_set,
            priming=priming,
            repeats=repeats,
            business=business,
            close_performs=closes,
            eoc_condition=eoc_condition,
        )

    # =================================================================
    # Path A
    # =================================================================
    def _repair_inline(
        self,
        lines: list[str],
        cursor_set: CursorParagraphSet,
        driving: CursorPerform,
        closes: list[CursorPerform],
        eoc_condition: str,
    ) -> list[str]:
        """INLINE already ran: only the condition and the CLOSE remain."""
        lines = self.repair.normalise_perform_line(
            lines=lines,
            index=driving.index,
            condition=eoc_condition,
            cursor=cursor_set.cursor,
        )
        return self.repair.guarantee_close(
            lines=lines,
            after_index=driving.index,
            cursor_set=cursor_set,
            close_performs=closes,
        )

    # =================================================================
    # Path B
    # =================================================================
    def _repair_span(
        self,
        lines: list[str],
        cursor_set: CursorParagraphSet,
        loop,
        closes: list[CursorPerform],
        eoc_condition: str,
    ) -> list[str]:
        """SPAN shape: the in-loop fetch is REQUIRED and stays put.

        Removing it would leave SQLCODE unchanged and the loop would run
        forever - the exact defect CursorFlowComposer records as
        CORRECTION 2.
        """
        lines = self.repair.normalise_loop(
            lines=lines,
            loop=loop,
            condition=eoc_condition,
            cursor=cursor_set.cursor,
        )
        return self.repair.guarantee_close(
            lines=lines,
            after_index=loop.end_index,
            cursor_set=cursor_set,
            close_performs=closes,
        )

    # =================================================================
    # Helpers
    # =================================================================
    def _business_paragraph(
        self,
        lines: list[str],
        repeats: list[CursorPerform],
    ) -> str:
        """The paragraph that used to carry the converted OBTAIN NEXT."""
        if not repeats:
            return ""

        headers = self.lines_utils.paragraph_headers(lines)
        return self.lines_utils.owner_paragraph(headers, repeats[0].index)


__all__ = ["CursorCloseGuaranteeComposer"]