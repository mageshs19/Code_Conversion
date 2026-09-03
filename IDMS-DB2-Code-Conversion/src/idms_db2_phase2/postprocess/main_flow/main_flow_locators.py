from __future__ import annotations

from patterns.update_main_flow_patterns import (
    OPEN_INPUT_LINE_PATTERN,
    STOP_RUN_LINE_PATTERN,
)
from rules.update_restart_rules import (
    MAIN_FLOW_LEGACY_RESTART_TOKENS,
    MAIN_FLOW_LONE_PERIOD,
    MAIN_FLOW_TOKEN_CLOSE,
)


class MainFlowLocators:
    """Index/region finders and insertion planning for the main flow."""

    def _find_open_input_index(self, *, lines, file_name):
        target = str(file_name or "").strip().upper()
        if not target:
            return -1

        for index, line in enumerate(lines):
            match = OPEN_INPUT_LINE_PATTERN.search(self._logical(line).upper())
            if not match:
                continue
            if str(match.group("file") or "").strip().upper() == target:
                return index
        return -1

    def _find_close_input_index(self, *, lines, file_name):
        target = str(file_name or "").strip().upper()
        if not target:
            return -1

        for index, line in enumerate(lines):
            logical = self._logical(line).upper()
            if not logical.startswith(MAIN_FLOW_TOKEN_CLOSE):
                continue
            if target in logical:
                return index
        return -1

    def _find_stop_run_index(self, *, lines, start_index):
        for index in range(start_index, len(lines)):
            if STOP_RUN_LINE_PATTERN.search(self._logical(lines[index]).upper()):
                return index
        return -1

    def _has_legacy_restart_between(self, *, lines, start_index, end_index):
        for index in range(start_index, end_index):
            upper = self._logical(lines[index]).upper()
            if any(token in upper for token in MAIN_FLOW_LEGACY_RESTART_TOKENS):
                return True
        return False

    def _read_next_insert_plan(self, *, lines, start, end):
        for index in range(end - 1, start, -1):
            logical = self._logical(lines[index])
            if not logical:
                continue
            if logical == MAIN_FLOW_LONE_PERIOD:
                return index, True
            if logical.endswith("."):
                return index + 1, False
        return end, False