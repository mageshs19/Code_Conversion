# LOCATION: src/idms_db2_phase2/composers/cleanup/residual_idms_comment_cleanup.py
# ACTION: CREATE NEW FILE

"""
Residual IDMS comment cleanup.

Removes advisory comment noise left by the IDMS->DB2 transformer, such as:
    * DB2: Removed residual IDMS control statement: IDMS-CONTROL
    * SECTION.
    * DB2: Removed IDMS FIND CURRENT statement: FIND CURRENT FFRECAB
    * DB2: IDMS record FFRECAB was not converted automatically.
    * DB2: Missing Sheet Mapping and DCLGEN metadata.
    * DB2: Restart/control logic requires manual DB2 redesign.

Safety:
- Only comment lines are removed (never executable code).
- A CONTINUE. left after a removed IDMS statement is removed only when it is
  redundant (another executable statement follows in the same block and the
  CONTINUE. is not the sole statement of an IF/ELSE/WHEN/EVALUATE branch).
"""

from __future__ import annotations

from idms_db2_phase2.composers.cleanup.cleanup_message_collector import (
    CleanupMessageCollector,
)
from idms_db2_phase2.composers.cleanup.cobol_cleanup_line_utils import (
    CobolCleanupLineUtils,
)
from patterns.cobol_cleanup_patterns import (
    BLOCK_OPENER_PATTERN,
    LONE_CONTINUE_PATTERN,
    RESIDUAL_IDMS_COMMENT_CONTINUATION_PATTERN,
    RESIDUAL_IDMS_COMMENT_PATTERN,
)

# UPDATE the import block at the top to include the new pattern:
from patterns.cobol_cleanup_patterns import (
    BLOCK_OPENER_PATTERN,
    LONE_CONTINUE_PATTERN,
    REMOVED_OBTAIN_CALC_COMMENT_PATTERN,
    RESIDUAL_IDMS_COMMENT_CONTINUATION_PATTERN,
    RESIDUAL_IDMS_COMMENT_PATTERN,
)

class ResidualIdmsCommentCleanup:
    def __init__(
        self,
        messages: CleanupMessageCollector,
        line_utils: CobolCleanupLineUtils | None = None,
    ) -> None:
        self.messages = messages
        self.line_utils = line_utils or CobolCleanupLineUtils()

    def _logical(self, line: str) -> str:
        return self.line_utils.logical(line)

    def remove_residual_idms_comments(self, text: str) -> str:
        lines = text.splitlines()
        output: list[str] = []
        removed_comment = False
        index = 0

        while index < len(lines):
            line = lines[index]
            logical = self._logical(line)

            if (
                RESIDUAL_IDMS_COMMENT_PATTERN.match(logical)
                or REMOVED_OBTAIN_CALC_COMMENT_PATTERN.match(logical)
            ):
                index = self._skip_comment_group(lines, index)
                removed_comment = True
                index = self._maybe_skip_redundant_continue(
                    lines=lines,
                    index=index,
                    output=output,
                )
                continue

            output.append(line)
            index += 1

        if removed_comment:
            self.messages.add("removed_residual_idms_comment")

        return "\n".join(output).rstrip() + "\n"
            
    def _skip_comment_group(
        self,
        lines: list[str],
        index: int,
    ) -> int:
        """
        Skip the residual DB2 comment line plus any immediate continuation or
        related DB2 comment lines (residual, OBTAIN CALC removal, or wrapped).
        """
        index += 1
        while index < len(lines):
            logical = self._logical(lines[index])
            if RESIDUAL_IDMS_COMMENT_PATTERN.match(logical):
                index += 1
                continue
            if REMOVED_OBTAIN_CALC_COMMENT_PATTERN.match(logical):
                index += 1
                continue
            if RESIDUAL_IDMS_COMMENT_CONTINUATION_PATTERN.match(logical):
                index += 1
                continue
            break
        return index
    
    def _maybe_skip_redundant_continue(
        self,
        lines: list[str],
        index: int,
        output: list[str],
    ) -> int:
        """
        If the next executable line is a lone CONTINUE., remove it only when
        it is safe: it must NOT be the sole statement of an IF/ELSE/WHEN/
        EVALUATE branch, and another executable statement (or END-IF/END-
        EVALUATE/period) must not depend on it.
        """
        if index >= len(lines):
            return index

        logical = self._logical(lines[index])
        if not LONE_CONTINUE_PATTERN.match(logical):
            return index

        # Look at the previous emitted executable line.
        prev_opener = self._previous_is_block_opener(output)

        # Look ahead to the next non-blank, non-comment logical line.
        next_logical = self._next_executable_logical(lines, index + 1)
        next_upper = next_logical.upper()

        closes_block = (
            next_upper.startswith("END-IF")
            or next_upper.startswith("END-EVALUATE")
            or next_upper.startswith("ELSE")
            or next_upper.startswith("WHEN")
            or next_upper == "."
        )

        # If CONTINUE. is the only body of a branch, KEEP it (branch must
        # not be empty).
        if prev_opener and closes_block:
            return index

        # Otherwise it is redundant -> skip it.
        self.messages.add("removed_orphan_continue")
        return index + 1

    def _previous_is_block_opener(self, output: list[str]) -> bool:
        for line in reversed(output):
            logical = self._logical(line)
            if not logical:
                continue
            if logical.startswith("*"):
                continue
            return bool(BLOCK_OPENER_PATTERN.match(logical))
        return False

    def _next_executable_logical(
        self,
        lines: list[str],
        start_index: int,
    ) -> str:
        for index in range(start_index, len(lines)):
            logical = self._logical(lines[index])
            if not logical:
                continue
            if logical.startswith("*"):
                continue
            return logical
        return ""