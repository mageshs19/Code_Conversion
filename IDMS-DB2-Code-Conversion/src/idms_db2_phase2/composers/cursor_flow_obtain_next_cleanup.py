"""
Cursor flow OBTAIN NEXT cleanup.

Removes leftover generated OBTAIN NEXT cursor calls after a cursor has
already been converted to FETCH UNTIL EOC flow, replacing them with a
manual redesign comment and CONTINUE.
"""

from idms_db2_phase2.composers.cursor_flow_line_formatter import (
    CursorFlowLineFormatter,
)
from patterns.cursor_flow_patterns import (
    CONVERTED_OBTAIN_COMMENT_PATTERN,
    CONVERTED_OBTAIN_NEXT_COMMENT_PATTERN,
    PERFORM_CURSOR_PATTERN,
)
from rules.cursor_flow_rules import REMOVED_OBTAIN_NEXT_COMMENT


class CursorFlowObtainNextCleanup:
    def __init__(
        self,
        line_formatter: CursorFlowLineFormatter | None = None,
    ) -> None:
        self.line_formatter = line_formatter or CursorFlowLineFormatter()

    def _logical(self, line: str) -> str:
        return self.line_formatter.logical(line)

    def remove_leftover_obtain_next_cursor_calls(
        self,
        lines: list[str],
    ) -> list[str]:
        output: list[str] = []
        index = 0

        while index < len(lines):
            logical = self._logical(lines[index])

            if not CONVERTED_OBTAIN_NEXT_COMMENT_PATTERN.match(logical):
                output.append(lines[index])
                index += 1
                continue

            skipped_lines = [lines[index]]
            index = self._skip_obtain_next_block(
                lines=lines,
                start_index=index + 1,
                skipped_lines=skipped_lines,
            )

            output.append(
                self.line_formatter.format_like_line(
                    reference_line=skipped_lines[0],
                    replacement_body=REMOVED_OBTAIN_NEXT_COMMENT,
                )
            )
            output.append(
                self.line_formatter.format_like_line(
                    reference_line=skipped_lines[0],
                    replacement_body="CONTINUE.",
                )
            )

        return output

    def _skip_obtain_next_block(
        self,
        lines: list[str],
        start_index: int,
        skipped_lines: list[str],
    ) -> int:
        index = start_index

        while index < len(lines):
            next_logical = self._logical(lines[index])

            if not next_logical:
                skipped_lines.append(lines[index])
                index += 1
                continue

            if next_logical.startswith("*") and not (
                CONVERTED_OBTAIN_COMMENT_PATTERN.match(next_logical)
            ):
                break

            if CONVERTED_OBTAIN_COMMENT_PATTERN.match(next_logical):
                break

            if PERFORM_CURSOR_PATTERN.match(next_logical):
                skipped_lines.append(lines[index])
                index += 1
                continue

            break

        return index