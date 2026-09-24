# LOCATION: src/idms_db2_phase2/composers/cursor_close_guarantee/close_guarantor.py
# ACTION: CREATE NEW FILE

"""Guarantees that a generated CLOSE paragraph is actually performed.

A declared-but-never-performed CLOSE paragraph leaks the cursor. DB2
holds the result set until the thread ends, and with WITH HOLD it
survives a COMMIT, so a long batch accumulates open cursors until it
abends on resource limits.
"""

from __future__ import annotations

from idms_db2_phase2.composers.cursor_close_guarantee.line_utils import (
    CursorGuaranteeLineUtils,
)
from idms_db2_phase2.composers.cursor_close_guarantee.message_log import (
    MessageLog,
)
from idms_db2_phase2.composers.cursor_close_guarantee.models import (
    CursorParagraphSet,
    CursorPerform,
)
from rules.cursor_close_guarantee_rules import PERFORM_CLOSE_TEMPLATE


class CloseGuarantor:
    """Inserts the missing PERFORM of a cursor CLOSE paragraph."""

    def __init__(
        self,
        line_utils: CursorGuaranteeLineUtils | None = None,
        log: MessageLog | None = None,
    ) -> None:
        self.lines_utils = line_utils or CursorGuaranteeLineUtils()
        self.log = log or MessageLog()

    def guarantee(
        self,
        lines: list[str],
        after_index: int,
        cursor_set: CursorParagraphSet,
        close_performs: list[CursorPerform],
    ) -> list[str]:
        """Insert PERFORM <close>. after `after_index` when it is absent."""
        if close_performs:
            self.log.log("close_present", close=cursor_set.close_name)
            return lines

        if not 0 <= after_index < len(lines):
            return lines

        close_line = self.lines_utils.format_like(
            reference_line=lines[after_index],
            body=PERFORM_CLOSE_TEMPLATE.format(close=cursor_set.close_name),
        )

        output = list(lines)
        output.insert(after_index + 1, close_line)

        self.log.log(
            "close_inserted",
            close=cursor_set.close_name,
            cursor=cursor_set.cursor,
        )

        return output


__all__ = ["CloseGuarantor"]