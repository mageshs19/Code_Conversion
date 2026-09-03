from __future__ import annotations

from collections import Counter

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from idms_db2_phase2.services.update_cobol_final_cleanup_utils import (
    UpdateCobolFinalCleanupUtils,
)
from patterns.update_final_feedback_patterns import (
    DCLGEN_OF_REFERENCE_PATTERN,
    EXEC_SQL_END_PATTERN,
    EXEC_SQL_START_PATTERN,
    INITIALIZE_DCL_PATTERN,
    MOVE_TO_BARE_RECORD_PATTERN,
    NON_SQL_DCL_DOT_REFERENCE_PATTERN,
    SQL_LOCATION_DB_OPERATION_PATTERN,
)
from rules.update_cobol_final_cleanup_rules import (
    UPDATE_FINAL_LOOKAHEAD_LIMIT,
    UPDATE_FINAL_LOOKBACK_DUPLICATE_LIMIT,
)


class UpdateCobolReferenceCleanup:
    """
    Handles non-SQL DCLGEN reference cleanup and safe bare-record initialization.

    Responsibilities:
    - Convert non-SQL DCLGROUP.HOST references to HOST OF DCLGROUP.
    - Replace MOVE SPACES TO bare-record with INITIALIZE DCLGROUP only when
      nearby DCLGEN context is clear.
    """

    def __init__(
        self,
        *,
        fixed_format: FixedFormatLineService,
        utils: UpdateCobolFinalCleanupUtils,
    ) -> None:
        self.fixed_format = fixed_format
        self.utils = utils

    def normalize_non_sql_dcl_dot_references(
        self,
        text: str,
    ) -> str:
        lines = text.splitlines()
        output: list[str] = []
        in_exec_sql = False

        for line in lines:
            logical = self.fixed_format.logical(line)

            if EXEC_SQL_START_PATTERN.match(logical):
                in_exec_sql = True
                output.append(line)
                continue

            if in_exec_sql:
                output.append(line)

                if EXEC_SQL_END_PATTERN.match(logical):
                    in_exec_sql = False

                continue

            updated_logical = NON_SQL_DCL_DOT_REFERENCE_PATTERN.sub(
                self._replace_dcl_dot_with_of,
                logical,
            )

            if updated_logical == logical:
                output.append(line)
                continue

            output.append(
                self.fixed_format.replace_body(
                    line,
                    self.utils.body_with_existing_indent(
                        original_line=line,
                        new_logical=updated_logical,
                    ),
                )
            )

        return "\n".join(output).rstrip() + "\n"

    def replace_bare_record_initialization(
        self,
        text: str,
    ) -> str:
        lines = text.splitlines()
        output: list[str] = []
        in_exec_sql = False

        for index, line in enumerate(lines):
            logical = self.fixed_format.logical(line)

            if EXEC_SQL_START_PATTERN.match(logical):
                in_exec_sql = True
                output.append(line)
                continue

            if in_exec_sql:
                output.append(line)

                if EXEC_SQL_END_PATTERN.match(logical):
                    in_exec_sql = False

                continue

            if self.fixed_format.is_comment_or_control_line(line):
                output.append(line)
                continue

            match = MOVE_TO_BARE_RECORD_PATTERN.match(logical)

            if not match:
                output.append(line)
                continue

            target = str(match.group("target") or "").upper()

            if self.utils.is_protected_bare_target(target):
                output.append(line)
                continue

            group = self.nearest_dcl_group_after(
                lines=lines,
                start_index=index + 1,
            )

            if not group:
                output.append(line)
                continue

            if self.recent_output_has_initialize(output, group):
                output.append(line)
                continue

            output.append(
                self.fixed_format.replace_body(
                    line,
                    self.utils.body_with_existing_indent(
                        original_line=line,
                        new_logical=f"INITIALIZE {group}",
                    ),
                )
            )

        return "\n".join(output).rstrip() + "\n"

    def nearest_dcl_group_after(
        self,
        *,
        lines: list[str],
        start_index: int,
    ) -> str:
        groups: list[str] = []
        in_exec_sql = False

        for index in range(
            start_index,
            min(len(lines), start_index + UPDATE_FINAL_LOOKAHEAD_LIMIT),
        ):
            logical = self.fixed_format.logical(lines[index])

            if EXEC_SQL_START_PATTERN.match(logical):
                in_exec_sql = True
                continue

            if in_exec_sql:
                if EXEC_SQL_END_PATTERN.match(logical):
                    in_exec_sql = False
                continue

            for match in DCLGEN_OF_REFERENCE_PATTERN.finditer(logical):
                group = str(match.group("group") or "").upper()

                if group:
                    groups.append(group)

            for match in NON_SQL_DCL_DOT_REFERENCE_PATTERN.finditer(logical):
                group = str(match.group("group") or "").upper()

                if group:
                    groups.append(group)

            if SQL_LOCATION_DB_OPERATION_PATTERN.match(logical):
                break

        if not groups:
            return ""

        return Counter(groups).most_common(1)[0][0]

    def recent_output_has_initialize(
        self,
        output: list[str],
        group: str,
    ) -> bool:
        target = str(group or "").upper()
        start = max(0, len(output) - UPDATE_FINAL_LOOKBACK_DUPLICATE_LIMIT)

        for index in range(len(output) - 1, start - 1, -1):
            logical = self.fixed_format.logical(output[index])
            match = INITIALIZE_DCL_PATTERN.match(logical)

            if match and str(match.group("group") or "").upper() == target:
                return True

        return False

    def _replace_dcl_dot_with_of(
        self,
        match,
    ) -> str:
        group = str(match.group("group") or "").upper()
        host = str(match.group("host") or "").upper()

        return f"{host} OF {group}"