"""
Child fetch early-stop cleanup.

Adds an SW-STATUS-D early-stop condition to nested child cursor fetch loops,
keeping the stop condition in the manual-style two-line form.
"""

from idms_db2_phase2.composers.cleanup.cleanup_message_collector import (
    CleanupMessageCollector,
)
from idms_db2_phase2.composers.cleanup.cobol_cleanup_line_utils import (
    CobolCleanupLineUtils,
)
from patterns.cobol_cleanup_patterns import (
    FETCH_PARAGRAPH_NUMBER_PATTERN,
    FETCH_UNTIL_EOC_FULL_SW_PATTERN,
    FETCH_UNTIL_EOC_OR_SW_PATTERN,
    FETCH_UNTIL_EOC_PATTERN,
    SW_STATUS_D_MOVE_N_PATTERN,
    SW_STATUS_Y_CONTINUATION_PATTERN,
)
from rules.cobol_cleanup_rules import (
    CHILD_FETCH_MINIMUM_NUMBER,
    MOVE_N_LOOKBACK_WINDOW,
)

SW_STATUS_Y_CONTINUATION_INDENT = "                             "


class ChildFetchEarlyStopCleanup:
    def __init__(
        self,
        messages: CleanupMessageCollector,
        line_utils: CobolCleanupLineUtils | None = None,
    ) -> None:
        self.messages = messages
        self.line_utils = line_utils or CobolCleanupLineUtils()

    def _logical(self, line: str) -> str:
        return self.line_utils.logical(line)

    def _leading_spaces(self, line: str) -> str:
        return self.line_utils.leading_spaces(line)

    def ensure_child_fetch_early_stop(self, text: str) -> str:
        if "SW-STATUS-D" not in text:
            return text

        lines = text.splitlines()
        output: list[str] = []
        changed = False
        index = 0

        while index < len(lines):
            line = lines[index]
            logical = self._logical(line)

            full_match = FETCH_UNTIL_EOC_FULL_SW_PATTERN.match(logical)
            if full_match and self._is_child_or_nested_fetch(
                full_match.group("fetch")
            ):
                self._append_early_stop(output, line, full_match)
                changed = True
                index += 1
                continue

            or_match = FETCH_UNTIL_EOC_OR_SW_PATTERN.match(logical)
            if or_match and self._is_child_or_nested_fetch(
                or_match.group("fetch")
            ):
                self._append_early_stop(output, line, or_match)
                changed = True

                if self._next_line_is_sw_status_y_continuation(lines, index):
                    index += 2
                else:
                    index += 1
                continue

            match = FETCH_UNTIL_EOC_PATTERN.match(logical)
            if match and self._is_child_or_nested_fetch(match.group("fetch")):
                self._append_early_stop(output, line, match)
                changed = True
                index += 1
                continue

            output.append(line)
            index += 1

        if changed:
            self.messages.add("child_fetch_early_stop")

        return "\n".join(output).rstrip() + "\n"

    def _append_early_stop(
        self,
        output: list[str],
        line: str,
        match,
    ) -> None:
        leading = self._leading_spaces(line)
        fetch_paragraph = match.group("fetch")
        eoc_flag = match.group("eoc")

        if not self._previous_output_has_move_n(output):
            output.append(f"{leading}MOVE 'N' TO SW-STATUS-D")

        output.append(
            f"{leading}PERFORM {fetch_paragraph} UNTIL {eoc_flag} OR"
        )
        output.append(
            f"{leading}{SW_STATUS_Y_CONTINUATION_INDENT}SW-STATUS-D = 'Y'"
        )

    def _next_line_is_sw_status_y_continuation(
        self,
        lines: list[str],
        index: int,
    ) -> bool:
        if index + 1 >= len(lines):
            return False

        logical = self._logical(lines[index + 1])
        return bool(SW_STATUS_Y_CONTINUATION_PATTERN.match(logical))

    def _previous_output_has_move_n(self, output: list[str]) -> bool:
        lookback = output[-MOVE_N_LOOKBACK_WINDOW:]
        return any(
            SW_STATUS_D_MOVE_N_PATTERN.match(self._logical(line))
            for line in lookback
        )

    def _is_child_or_nested_fetch(self, fetch_paragraph: str) -> bool:
        paragraph = str(fetch_paragraph or "").upper()
        match = FETCH_PARAGRAPH_NUMBER_PATTERN.match(paragraph)

        if not match:
            return False

        try:
            number = int(match.group("number"))
        except ValueError:
            return False

        return number >= CHILD_FETCH_MINIMUM_NUMBER