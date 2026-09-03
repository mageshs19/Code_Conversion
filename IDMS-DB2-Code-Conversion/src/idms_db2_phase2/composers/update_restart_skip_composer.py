from __future__ import annotations

from patterns.sequence_patterns import strip_sequence_numbers
from patterns.update_restart_skip_patterns import (
    CONTINUE_PATTERN,
    CONVERTED_FOR_PATTERN,
    DB2_COMMENT_PATTERN,
    END_IF_PATTERN,
    REMOVED_OBTAIN_CALC_PATTERN,
    SKIPPED_FOR_PATTERN,
    SQLCODE_IF_PATTERN,
)
from rules.update_restart_skip_rules import (
    EMIT_MANUAL_REDESIGN_MESSAGE,
    MANUAL_REDESIGN_MESSAGE_TEMPLATE,
    MISSING_MAPPING_MARKERS,
    REPLACEMENT_BLOCK_TEMPLATES,
    RESTART_CONTROL_HINTS,
)


class UpdateRestartSkipComposer:
    """Cleans generated missing-mapping blocks for unmapped restart/control
    records.

    Generic rule:
    - Do not hardcode any record to a DB2 restart table.
    - Do not invent DB2 restart SQL.
    - Replace skipped/converted-with-missing-mapping restart/control blocks
      with a manual-redesign comment and CONTINUE.
    - Remove SQLCODE checks after skipped SQL (no SQL was executed).

    Regex lives in patterns/update_restart_skip_patterns.py; markers, hints,
    the replacement block, and messages in
    rules/update_restart_skip_rules.py.
    """

    def __init__(self) -> None:
        self.messages: list[str] = []

    def compose(self, text: str) -> str:
        self.messages = []
        if not text:
            return ""

        lines = self._normalize_line_endings(text).splitlines()
        output: list[str] = []
        index = 0

        while index < len(lines):
            logical = self._logical(lines[index])

            removed_obtain_match = REMOVED_OBTAIN_CALC_PATTERN.match(logical)
            skipped_match = SKIPPED_FOR_PATTERN.match(logical)
            converted_match = CONVERTED_FOR_PATTERN.match(logical)

            if removed_obtain_match:
                index = self._handle_restart_block(
                    lines=lines,
                    index=index,
                    output=output,
                    record_name=removed_obtain_match.group("record"),
                    require_missing_marker=False,
                )
                continue

            if skipped_match:
                index = self._handle_restart_block(
                    lines=lines,
                    index=index,
                    output=output,
                    record_name=skipped_match.group("record"),
                    require_missing_marker=False,
                )
                continue

            if converted_match:
                index = self._handle_restart_block(
                    lines=lines,
                    index=index,
                    output=output,
                    record_name=converted_match.group("record"),
                    require_missing_marker=True,
                )
                continue

            output.append(lines[index])
            index += 1

        return "\n".join(output).rstrip() + "\n"

    def _handle_restart_block(
        self,
        *,
        lines: list[str],
        index: int,
        output: list[str],
        record_name: str,
        require_missing_marker: bool,
    ) -> int:
        record = str(record_name or "").upper()

        if not self._looks_like_restart_or_control(record):
            output.append(lines[index])
            return index + 1

        block_end = self._block_end(lines=lines, start_index=index)

        if require_missing_marker and not self._contains_missing_mapping_marker(
            lines[index:block_end]
        ):
            output.append(lines[index])
            return index + 1

        output.extend(self._replacement_block(record))
        next_index = self._skip_following_sqlcode_blocks(
            lines=lines, start_index=block_end
        )
        self._note_manual_redesign(record)
        return next_index

    def _block_end(self, lines: list[str], start_index: int) -> int:
        """Advance past a generated comment block ending in CONTINUE.

        Shared by the removed-OBTAIN-CALC, skipped, and converted cases
        (their scanning logic is identical).
        """
        index = start_index + 1

        while index < len(lines):
            logical = self._logical(lines[index])

            if not logical:
                index += 1
                continue
            if DB2_COMMENT_PATTERN.match(logical):
                index += 1
                continue
            if CONTINUE_PATTERN.match(logical):
                index += 1
                break

            break

        return index

    def _contains_missing_mapping_marker(self, lines: list[str]) -> bool:
        combined = "\n".join(self._logical(line).upper() for line in lines)
        return any(marker in combined for marker in MISSING_MAPPING_MARKERS)

    def _note_manual_redesign(self, record_name: str) -> None:
        if not EMIT_MANUAL_REDESIGN_MESSAGE:
            return
        self.messages.append(
            MANUAL_REDESIGN_MESSAGE_TEMPLATE.format(record_name=record_name)
        )

    def _replacement_block(self, record_name: str) -> list[str]:
        return [
            template.format(record=record_name)
            for template in REPLACEMENT_BLOCK_TEMPLATES
        ]

    def _looks_like_restart_or_control(self, record_name: str) -> bool:
        normalized = str(record_name or "").upper()
        return any(hint in normalized for hint in RESTART_CONTROL_HINTS)

    def _skip_following_sqlcode_blocks(
        self, lines: list[str], start_index: int
    ) -> int:
        index = start_index
        while index < len(lines):
            if not SQLCODE_IF_PATTERN.match(self._logical(lines[index])):
                break
            index = self._skip_if_block(lines=lines, start_index=index)
        return index

    def _skip_if_block(self, lines: list[str], start_index: int) -> int:
        index = start_index
        while index < len(lines):
            logical = self._logical(lines[index])
            index += 1
            if END_IF_PATTERN.match(logical):
                break
        return index

    def _logical(self, line: str) -> str:
        return strip_sequence_numbers(str(line or "")).strip()

    def _normalize_line_endings(self, text: str) -> str:
        return str(text or "").replace("\r\n", "\n").replace("\r", "\n")