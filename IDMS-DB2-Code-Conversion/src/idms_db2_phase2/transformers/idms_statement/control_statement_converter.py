from __future__ import annotations

from patterns.idms_patterns import (
    BIND_STATEMENT_PATTERN,
    COMMIT_PATTERN,
    CONNECT_STATEMENT_PATTERN,
    DISCONNECT_STATEMENT_PATTERN,
    FINISH_PATTERN,
    IDMS_ABORT_PERFORM_PATTERN,
    IDMS_STATUS_PERFORM_PATTERN,
    READY_PATTERN,
    USAGE_MODE_PATTERN,
)
from rules.idms_transformer_messages import (
    COMMIT_OUTSIDE_PROCEDURE_TEMPLATE,
    FINISH_CONVERTED_TO_COMMIT,
    FINISH_OUTSIDE_PROCEDURE_TEMPLATE,
    REMOVED_BIND_TEMPLATE,
    REMOVED_CONNECT_TEMPLATE,
    REMOVED_CONTROL_STATEMENT_TEMPLATE,
    REMOVED_DISCONNECT_TEMPLATE,
    REMOVED_STATUS_ABORT_TEMPLATE,
    REMOVED_USAGE_READY_TEMPLATE,
)
from rules.idms_transformer_rules import PROCEDURE_DIVISION_NAME


class ControlStatementConverterMixin:
    """Converts IDMS declarative/control statements to DB2 comments."""

    def _convert_declarative_or_control(self, upper, stripped_line):
        if not self._is_idms_declarative_or_control_statement(upper):
            return None
        return [
            REMOVED_CONTROL_STATEMENT_TEMPLATE.format(line=stripped_line),
        ]

    def _convert_finish_or_commit(self, upper, stripped_line, current_division):
        if FINISH_PATTERN.search(upper):
            if current_division != PROCEDURE_DIVISION_NAME:
                return [
                    FINISH_OUTSIDE_PROCEDURE_TEMPLATE.format(line=stripped_line)
                ]
            return [FINISH_CONVERTED_TO_COMMIT, *self.sql_generator.commit()]

        if COMMIT_PATTERN.search(upper) and "EXEC SQL" not in upper:
            if current_division != PROCEDURE_DIVISION_NAME:
                return [
                    COMMIT_OUTSIDE_PROCEDURE_TEMPLATE.format(line=stripped_line)
                ]
            return self.sql_generator.commit()

        return None

    def _convert_bind_ready_connect_disconnect(
        self, upper, stripped_line, current_division
    ):
        if BIND_STATEMENT_PATTERN.search(upper):
            return self._removed_idms_executable_lines(
                message=REMOVED_BIND_TEMPLATE.format(line=stripped_line),
                current_division=current_division,
            )

        if READY_PATTERN.search(upper) or USAGE_MODE_PATTERN.search(upper):
            return self._removed_idms_executable_lines(
                message=REMOVED_USAGE_READY_TEMPLATE.format(line=stripped_line),
                current_division=current_division,
            )

        if CONNECT_STATEMENT_PATTERN.search(upper):
            return self._removed_idms_executable_lines(
                message=REMOVED_CONNECT_TEMPLATE.format(line=stripped_line),
                current_division=current_division,
            )

        if DISCONNECT_STATEMENT_PATTERN.search(upper):
            return self._removed_idms_executable_lines(
                message=REMOVED_DISCONNECT_TEMPLATE.format(line=stripped_line),
                current_division=current_division,
            )

        return None

    def _convert_status_abort_perform(
        self, upper, stripped_line, current_division
    ):
        if IDMS_STATUS_PERFORM_PATTERN.search(upper) or (
            IDMS_ABORT_PERFORM_PATTERN.search(upper)
        ):
            return self._removed_idms_executable_lines(
                message=REMOVED_STATUS_ABORT_TEMPLATE.format(line=stripped_line),
                current_division=current_division,
            )
        return None