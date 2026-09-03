from __future__ import annotations

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from idms_db2_phase2.services.update_cobol_final_cleanup_utils import (
    UpdateCobolFinalCleanupUtils,
)
from patterns.update_final_feedback_patterns import (
    CONVERTED_DB2_OPERATION_COMMENT_PATTERN,
    EXEC_SQL_END_PATTERN,
    EXEC_SQL_START_PATTERN,
    FROM_STATEMENT_PATTERN,
    SQL_LOCATION_DB_OPERATION_PATTERN,
    UPDATE_STATEMENT_PATTERN,
)
from rules.update_cobol_final_cleanup_rules import UPDATE_FINAL_LOOKAHEAD_LIMIT


class UpdateDiagnosticLabelNormalizer:
    """
    Rewrites generated DB2 diagnostic labels from IDMS record naming to nearby
    resolved DB2 table naming when SQL context is available.
    """

    def __init__(
        self,
        *,
        fixed_format: FixedFormatLineService,
        utils: UpdateCobolFinalCleanupUtils,
    ) -> None:
        self.fixed_format = fixed_format
        self.utils = utils

    def normalize_db2_diagnostic_labels(
        self,
        text: str,
    ) -> str:
        lines = text.splitlines()
        output: list[str] = []

        for index, line in enumerate(lines):
            logical = self.fixed_format.logical(line)

            sql_location_match = SQL_LOCATION_DB_OPERATION_PATTERN.match(logical)

            if sql_location_match:
                replacement = self._replacement_sql_location(
                    line=line,
                    lines=lines,
                    start_index=index + 1,
                    operation=str(sql_location_match.group("operation") or ""),
                )

                if replacement:
                    output.append(replacement)
                    continue

            comment_match = CONVERTED_DB2_OPERATION_COMMENT_PATTERN.match(logical)

            if comment_match:
                replacement = self._replacement_comment(
                    line=line,
                    lines=lines,
                    start_index=index + 1,
                    operation_text=str(comment_match.group("operation") or ""),
                    prefix=str(comment_match.group("prefix") or ""),
                    suffix=str(comment_match.group("suffix") or "."),
                )

                if replacement:
                    output.append(replacement)
                    continue

            output.append(line)

        return "\n".join(output).rstrip() + "\n"

    def _replacement_sql_location(
        self,
        *,
        line: str,
        lines: list[str],
        start_index: int,
        operation: str,
    ) -> str:
        table = self.nearby_table_for_operation(
            lines=lines,
            start_index=start_index,
            operation=operation,
        )

        if not table:
            return ""

        operation_name = str(operation or "").upper()

        return self.fixed_format.replace_body(
            line,
            self.utils.body_with_existing_indent(
                original_line=line,
                new_logical=f"MOVE '{operation_name}-{table}' TO SQL-LOCATION.",
            ),
        )

    def _replacement_comment(
        self,
        *,
        line: str,
        lines: list[str],
        start_index: int,
        operation_text: str,
        prefix: str,
        suffix: str,
    ) -> str:
        table = self.nearby_table_for_comment_operation(
            lines=lines,
            start_index=start_index,
            operation_text=operation_text,
        )

        if not table:
            return ""

        updated_comment = prefix + table + suffix

        return self.fixed_format.replace_body(
            line,
            self.utils.comment_body_for_line(
                original_line=line,
                comment_text=updated_comment,
            ),
        )

    def nearby_table_for_comment_operation(
        self,
        *,
        lines: list[str],
        start_index: int,
        operation_text: str,
    ) -> str:
        normalized = str(operation_text or "").upper()

        if "MODIFY" in normalized:
            return self.nearby_table_for_operation(
                lines=lines,
                start_index=start_index,
                operation="UPDATE",
            )

        if "OBTAIN" in normalized or "FIND" in normalized:
            return self.nearby_table_for_operation(
                lines=lines,
                start_index=start_index,
                operation="SELECT",
            )

        if "STORE" in normalized:
            return self.nearby_table_for_operation(
                lines=lines,
                start_index=start_index,
                operation="INSERT",
            )

        if "ERASE" in normalized:
            return self.nearby_table_for_operation(
                lines=lines,
                start_index=start_index,
                operation="DELETE",
            )

        return ""

    def nearby_table_for_operation(
        self,
        *,
        lines: list[str],
        start_index: int,
        operation: str,
    ) -> str:
        wanted_operation = str(operation or "").upper()
        in_exec_sql = False

        for index in range(
            start_index,
            min(len(lines), start_index + UPDATE_FINAL_LOOKAHEAD_LIMIT),
        ):
            logical = self.fixed_format.logical(lines[index])

            if EXEC_SQL_START_PATTERN.match(logical):
                in_exec_sql = True
                continue

            if in_exec_sql and EXEC_SQL_END_PATTERN.match(logical):
                in_exec_sql = False
                continue

            if wanted_operation == "UPDATE":
                update_match = UPDATE_STATEMENT_PATTERN.match(logical)

                if update_match:
                    return str(update_match.group("table") or "").upper()

            if wanted_operation == "SELECT":
                from_match = FROM_STATEMENT_PATTERN.match(logical)

                if from_match:
                    return str(from_match.group("table") or "").upper()

            if wanted_operation in {"INSERT", "DELETE"}:
                table = self.table_for_insert_or_delete(logical)

                if table:
                    return table

        return ""

    def table_for_insert_or_delete(
        self,
        logical: str,
    ) -> str:
        text = str(logical or "").strip().upper()
        parts = text.split()

        if len(parts) < 3:
            return ""

        if parts[0] == "INSERT" and parts[1] == "INTO":
            return parts[2]

        if parts[0] == "DELETE" and parts[1] == "FROM":
            return parts[2]

        return ""