# LOCATION: src/idms_db2_phase2/composers/cursor_close_guarantee/condition_normaliser.py
# ACTION: CREATE NEW FILE

"""Rewrites a legacy loop exit test to the cursor end-of-cursor flag.

    UNTIL SQLCODE = 100      ->  UNTIL DZBFASC1-EOC
    UNTIL DB-END-OF-SET      ->  UNTIL DZBFASC1-EOC

A condition that is NOT in LEGACY_EOC_CONDITIONS is left exactly as it
is. Rewriting an unrecognised business condition would change working
program logic, which the business-flow preservation rule forbids.
"""

from __future__ import annotations

from idms_db2_phase2.composers.cursor_close_guarantee.line_utils import (
    CursorGuaranteeLineUtils,
)
from idms_db2_phase2.composers.cursor_close_guarantee.message_log import (
    MessageLog,
)
from idms_db2_phase2.composers.cursor_close_guarantee.models import LoopShape
from rules.cursor_close_guarantee_rules import (
    STATEMENT_TERMINATOR,
    UNTIL_TEMPLATE,
)


class ConditionNormaliser:
    """Normalises loop exit conditions onto the cursor EOC flag."""

    def __init__(
        self,
        line_utils: CursorGuaranteeLineUtils | None = None,
        log: MessageLog | None = None,
    ) -> None:
        self.lines_utils = line_utils or CursorGuaranteeLineUtils()
        self.log = log or MessageLog()

    #
    # PERFORM <fetch> UNTIL <cond>.
    #
    def normalise_perform_line(
        self,
        lines: list[str],
        index: int,
        condition: str,
        cursor: str,
    ) -> list[str]:
        if not 0 <= index < len(lines):
            return lines

        logical = self.lines_utils.logical(lines[index])
        head, keyword, tail = self.lines_utils.partition_until(logical)

        if not keyword or not tail:
            return lines

        current = tail.rstrip(STATEMENT_TERMINATOR).strip()

        if not self._needs_rewrite(current, condition):
            return lines

        body = f"{head.rstrip()} {UNTIL_TEMPLATE.format(condition=condition)}"

        return self._write(
            lines=lines,
            index=index,
            body=body,
            terminated=self.lines_utils.is_terminated(logical),
            cursor=cursor,
            condition=condition,
        )

    #
    # A business driving loop
    #
    def normalise_loop(
        self,
        lines: list[str],
        loop: LoopShape,
        condition: str,
        cursor: str,
    ) -> list[str]:
        index = loop.until_index

        if not 0 <= index < len(lines):
            return lines

        if not self._needs_rewrite(loop.condition, condition):
            return lines

        logical = self.lines_utils.logical(lines[index])

        if self.lines_utils.is_until_only(logical):
            body = UNTIL_TEMPLATE.format(condition=condition)
        else:
            head, _keyword, _tail = self.lines_utils.partition_until(logical)
            body = (
                f"{head.rstrip()} "
                f"{UNTIL_TEMPLATE.format(condition=condition)}"
            )

        return self._write(
            lines=lines,
            index=index,
            body=body,
            terminated=loop.terminated,
            cursor=cursor,
            condition=condition,
        )

    #
    # Helpers
    #
    def _needs_rewrite(self, current: str, condition: str) -> bool:
        """Only a recognised legacy test is ever rewritten."""
        if self.lines_utils.compress(current) == self.lines_utils.compress(
            condition
        ):
            return False

        return self.lines_utils.is_legacy_condition(current)

    def _write(
        self,
        lines: list[str],
        index: int,
        body: str,
        terminated: bool,
        cursor: str,
        condition: str,
    ) -> list[str]:
        if terminated:
            body = f"{body}{STATEMENT_TERMINATOR}"

        output = list(lines)
        output[index] = self.lines_utils.format_like(
            reference_line=output[index],
            body=body,
        )

        self.log.log("condition_rewritten", cursor=cursor, condition=condition)

        return output


__all__ = ["ConditionNormaliser"]