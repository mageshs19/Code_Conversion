"""
ERROR-STATUS flag cleanup.

Replaces residual IDMS ERROR-STATUS loop control with a DB2 SW-STATUS-D flag
and declares SW-STATUS-D in Working-Storage only when it is needed.
"""

from idms_db2_phase2.composers.cleanup.cleanup_message_collector import (
    CleanupMessageCollector,
)
from idms_db2_phase2.composers.cleanup.cobol_cleanup_line_utils import (
    CobolCleanupLineUtils,
)
from patterns.cobol_cleanup_patterns import (
    ERROR_STATUS_MOVE_PATTERN,
    SW_STATUS_D_PIC_PATTERN,
    WORKING_STORAGE_PATTERN,
    WS_STATUS_PATTERN,
)
from rules.cobol_cleanup_rules import (
    SW_STATUS_D_DECLARATION,
    WS_DB2_FLAGS_GROUP,
)


class ErrorStatusFlagCleanup:
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

    def replace_error_status_with_flag(self, text: str) -> str:
        output_lines: list[str] = []
        replaced = False

        for line in text.splitlines():
            logical = self._logical(line)

            if ERROR_STATUS_MOVE_PATTERN.match(logical):
                leading = self._leading_spaces(line)
                output_lines.append(f"{leading}MOVE 'Y' TO SW-STATUS-D")
                replaced = True
                continue

            output_lines.append(line)

        if replaced:
            self.messages.add("replaced_error_status")

        return "\n".join(output_lines).rstrip() + "\n"

    def ensure_sw_status_d_declaration(self, text: str) -> str:
        if "SW-STATUS-D" not in text:
            return text

        if SW_STATUS_D_PIC_PATTERN.search(text):
            return text

        lines = text.splitlines()
        output: list[str] = []
        inserted = False

        for line in lines:
            output.append(line)

            if inserted:
                continue

            logical = self._logical(line)

            if WS_STATUS_PATTERN.match(logical):
                output.append(SW_STATUS_D_DECLARATION)
                inserted = True
                self.messages.add("declared_sw_status_d_ws")

        if inserted:
            return "\n".join(output).rstrip() + "\n"

        return self._insert_sw_status_d_after_working_storage(text)

    def _insert_sw_status_d_after_working_storage(self, text: str) -> str:
        lines = text.splitlines()
        output: list[str] = []
        inserted = False

        for line in lines:
            output.append(line)

            if inserted:
                continue

            logical = self._logical(line)

            if WORKING_STORAGE_PATTERN.match(logical):
                output.append(WS_DB2_FLAGS_GROUP)
                output.append(SW_STATUS_D_DECLARATION)
                inserted = True
                self.messages.add("declared_sw_status_d_block")

        if inserted:
            return "\n".join(output).rstrip() + "\n"

        return text