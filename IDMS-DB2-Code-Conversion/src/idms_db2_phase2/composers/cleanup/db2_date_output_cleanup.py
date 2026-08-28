"""
DB2 date output cleanup.

Converts a DB2 date host move (MOVE DA-/DT- OF DCLxxx TO UIT-/OUT- date
field) into the shared output-date realignment/conversion block before a
WRITE. Supports one-line and two-line MOVE forms.
"""

from idms_db2_phase2.composers.cleanup.cleanup_message_collector import (
    CleanupMessageCollector,
)
from idms_db2_phase2.composers.cleanup.cobol_cleanup_line_utils import (
    CobolCleanupLineUtils,
)
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.cobol_cleanup_patterns import (
    DB2_DATE_MOVE_ONE_LINE_PATTERN,
    DB2_DATE_MOVE_START_PATTERN,
    TO_UIT_DATE_FIELD_PATTERN,
)
from rules.db2_output_date_conversion_rules import (
    DB2_OUTPUT_DATE_CONVERSION_LINE_TEMPLATES,
    DB2_OUTPUT_DATE_HIGH_NUMERIC_LITERAL,
    DB2_OUTPUT_DATE_HIGH_VALUE_LITERAL,
    DB2_OUTPUT_DATE_LOW_VALUE_LITERAL,
)


class Db2DateOutputCleanup:
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

    def convert_db2_date_moves_to_output_dates(self, text: str) -> str:
        lines = text.splitlines()
        output: list[str] = []
        changed = False
        index = 0

        while index < len(lines):
            line = lines[index]
            logical = self._logical(line)

            one_line = DB2_DATE_MOVE_ONE_LINE_PATTERN.match(logical)

            if one_line:
                field = one_line.group("field")
                group = one_line.group("group")
                target = one_line.group("target")

                if self._should_generate_output_date_conversion(
                    field_name=field,
                    target_name=target,
                ):
                    output.extend(
                        self._date_conversion_lines(
                            leading=self._leading_spaces(line),
                            field=field,
                            group=group,
                            target=target,
                        )
                    )
                    changed = True
                    index += 1
                    continue

            start_match = DB2_DATE_MOVE_START_PATTERN.match(logical)

            if start_match and index + 1 < len(lines):
                next_logical = self._logical(lines[index + 1])
                target_match = TO_UIT_DATE_FIELD_PATTERN.match(next_logical)

                if target_match:
                    field = start_match.group("field")
                    group = start_match.group("group")
                    target = target_match.group("target")

                    if self._should_generate_output_date_conversion(
                        field_name=field,
                        target_name=target,
                    ):
                        output.extend(
                            self._date_conversion_lines(
                                leading=self._leading_spaces(line),
                                field=field,
                                group=group,
                                target=target,
                            )
                        )
                        changed = True
                        index += 2
                        continue

            output.append(line)
            index += 1

        if changed:
            self.messages.add("converted_db2_date_move")

        return "\n".join(output).rstrip() + "\n"

    def _should_generate_output_date_conversion(
        self,
        field_name: str,
        target_name: str,
    ) -> bool:
        """
        Return True only for DB2 date-host to output-date-field conversion.

        This prevents date ZEROES/SPACES logic from being generated for:
        - non-date output fields
        - DB2 DCLGEN host variables
        - update host moves
        - unrelated MOVE statements
        """
        field = str(field_name or "").strip().upper()
        target = str(target_name or "").strip().upper()

        if not field or not target:
            return False

        if not field.startswith(("DA-", "DT-")):
            return False

        if not target.startswith(
            ("UIT-DA-", "UIT-DT-", "OUT-DA-", "OUT-DT-")
        ):
            return False

        if " OF DCL" in target:
            return False

        if target.startswith("DCL"):
            return False

        return True

    def _date_conversion_lines(
        self,
        leading: str,
        field: str,
        group: str,
        target: str,
    ) -> list[str]:
        field_name = NameNormalizer.to_cobol(field)
        group_name = NameNormalizer.to_cobol(group)
        target_name = NameNormalizer.to_cobol(target)

        if not self._should_generate_output_date_conversion(
            field_name=field_name,
            target_name=target_name,
        ):
            return []

        output: list[str] = []

        for template in DB2_OUTPUT_DATE_CONVERSION_LINE_TEMPLATES:
            line = template.format(
                indent=leading,
                field_name=field_name,
                group_name=group_name,
                target_name=target_name,
                low_value=DB2_OUTPUT_DATE_LOW_VALUE_LITERAL,
                high_value=DB2_OUTPUT_DATE_HIGH_VALUE_LITERAL,
                high_numeric=DB2_OUTPUT_DATE_HIGH_NUMERIC_LITERAL,
            )

            if not line.strip():
                continue

            output.append(line.rstrip())

        return output