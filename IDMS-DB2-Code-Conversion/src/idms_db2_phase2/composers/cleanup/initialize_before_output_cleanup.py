"""
Initialize-before-output cleanup.

Ensures an INITIALIZE of the output record appears immediately before the
first output-field population MOVE preceding a WRITE, removing any duplicate
INITIALIZE for that record inside the population block.
"""

from idms_db2_phase2.composers.cleanup.cleanup_message_collector import (
    CleanupMessageCollector,
)
from idms_db2_phase2.composers.cleanup.cobol_cleanup_line_utils import (
    CobolCleanupLineUtils,
)
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.cobol_cleanup_patterns import (
    INITIALIZE_PATTERN,
    MOVE_START_PATTERN,
    MOVE_TO_OUTPUT_FIELD_PATTERN,
    TO_OUTPUT_FIELD_PATTERN,
    WRITE_PATTERN,
)
from rules.cobol_cleanup_rules import (
    INITIALIZE_LOOKBACK_WINDOW,
    OUTPUT_MOVE_SCAN_WINDOW,
    STOP_BACKWARD_SCAN_WORDS,
)


class InitializeBeforeOutputCleanup:
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

    def _is_comment_or_blank(self, logical: str) -> bool:
        return self.line_utils.is_comment_or_blank(logical)

    def ensure_initialize_before_output_population(self, text: str) -> str:
        lines = text.splitlines()
        output = list(lines)
        changed = False

        write_blocks = self._output_write_blocks(output)

        for block in reversed(write_blocks):
            write_index = int(block["write_index"])
            record = str(block["record"])
            first_move_index = int(block["first_move_index"])

            if write_index < 0 or first_move_index < 0:
                continue

            output, removed_count = (
                self._remove_initialize_for_record_in_range(
                    lines=output,
                    record=record,
                    start_index=first_move_index,
                    end_index=write_index,
                )
            )

            if removed_count:
                changed = True
                write_index -= removed_count

            if self._has_initialize_immediately_before(
                lines=output,
                index=first_move_index,
                record=record,
            ):
                continue

            leading = self._leading_spaces(output[first_move_index])
            output.insert(first_move_index, f"{leading}INITIALIZE {record}")
            changed = True
            self.messages.add("moved_initialize", record=record)

        if changed:
            return "\n".join(output).rstrip() + "\n"

        return text

    def _output_write_blocks(
        self,
        lines: list[str],
    ) -> list[dict[str, object]]:
        output: list[dict[str, object]] = []

        for index, line in enumerate(lines):
            logical = self._logical(line)
            match = WRITE_PATTERN.match(logical)

            if not match:
                continue

            record = match.group("record")
            first_move_index = (
                self._first_output_move_block_start_before_write(
                    lines=lines,
                    write_index=index,
                )
            )

            output.append(
                {
                    "write_index": index,
                    "record": record,
                    "first_move_index": first_move_index,
                }
            )

        return output

    def _first_output_move_block_start_before_write(
        self,
        lines: list[str],
        write_index: int,
    ) -> int:
        start = max(0, write_index - OUTPUT_MOVE_SCAN_WINDOW)
        first_move_start = -1

        for index in range(start, write_index):
            if self._line_targets_output_field(lines[index]):
                move_start = self._move_block_start(
                    lines=lines,
                    target_index=index,
                    search_start=start,
                )
                if move_start >= 0:
                    if first_move_start < 0 or move_start < first_move_start:
                        first_move_start = move_start

        return first_move_start

    def _line_targets_output_field(self, line: str) -> bool:
        logical = self._logical(line)

        if MOVE_TO_OUTPUT_FIELD_PATTERN.match(logical):
            return True

        if TO_OUTPUT_FIELD_PATTERN.match(logical):
            return True

        return False

    def _move_block_start(
        self,
        lines: list[str],
        target_index: int,
        search_start: int,
    ) -> int:
        logical = self._logical(lines[target_index])

        if MOVE_TO_OUTPUT_FIELD_PATTERN.match(logical):
            return target_index

        for index in range(target_index, search_start - 1, -1):
            candidate = self._logical(lines[index])
            upper = candidate.upper()

            if MOVE_START_PATTERN.match(candidate):
                return index

            if index == target_index:
                continue

            if self._is_comment_or_blank(candidate):
                continue

            if upper.startswith(STOP_BACKWARD_SCAN_WORDS):
                break

        return target_index

    def _remove_initialize_for_record_in_range(
        self,
        lines: list[str],
        record: str,
        start_index: int,
        end_index: int,
    ) -> tuple[list[str], int]:
        output: list[str] = []
        removed_count = 0

        for index, line in enumerate(lines):
            if start_index <= index < end_index:
                logical = self._logical(line)
                match = INITIALIZE_PATTERN.match(logical)

                if match:
                    current_record = NameNormalizer.normalize(
                        match.group("record")
                    )
                    target_record = NameNormalizer.normalize(record)

                    if current_record == target_record:
                        removed_count += 1
                        continue

            output.append(line)

        return output, removed_count

    def _has_initialize_immediately_before(
        self,
        lines: list[str],
        index: int,
        record: str,
    ) -> bool:
        lookback_start = max(0, index - INITIALIZE_LOOKBACK_WINDOW)
        target_record = NameNormalizer.normalize(record)

        for prior_index in range(lookback_start, index):
            logical = self._logical(lines[prior_index])
            match = INITIALIZE_PATTERN.match(logical)

            if not match:
                continue

            current_record = NameNormalizer.normalize(match.group("record"))

            if current_record == target_record:
                return True

        return False