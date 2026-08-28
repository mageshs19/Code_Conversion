"""
DB2 date field detector.

Scans generated COBOL lines to detect:
- DB2 date host fields compared with numeric COBOL date fields (PARMDATE).
- Shared DB2 date helper usage inside the PROCEDURE DIVISION.

Detection logic only. Owns no regex (patterns live in
patterns/db2_date_patterns.py) and no templates.
"""

from idms_db2_phase2.composers.db2_date_line_utils import Db2DateLineUtils
from patterns.db2_date_patterns import (
    DB2_DATE_COMPARISON_PATTERN,
    DB2_SHARED_DATE_HELPER_USAGE_PATTERN,
    PROCEDURE_DIVISION_PATTERN,
)


class Db2DateFieldDetector:
    def __init__(
        self,
        line_utils: Db2DateLineUtils | None = None,
    ) -> None:
        self.line_utils = line_utils or Db2DateLineUtils()

    def date_fields_used_in_comparisons(
        self,
        lines: list[str],
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for line in lines:
            logical = self.line_utils.logical(line)

            if self.line_utils.is_comment_or_blank(logical):
                continue

            match = DB2_DATE_COMPARISON_PATTERN.match(logical)

            if not match:
                continue

            field_name = self.line_utils.clean_cobol_name(match.group("field"))

            if not field_name:
                continue

            if field_name in seen:
                continue

            seen.add(field_name)
            output.append(field_name)

        return output

    def shared_date_helpers_used_in_procedure(
        self,
        lines: list[str],
    ) -> bool:
        in_procedure_division = False

        for line in lines:
            logical = self.line_utils.logical(line)

            if not logical:
                continue

            if PROCEDURE_DIVISION_PATTERN.match(logical):
                in_procedure_division = True
                continue

            if not in_procedure_division:
                continue

            if self.line_utils.is_comment_or_blank(logical):
                continue

            if DB2_SHARED_DATE_HELPER_USAGE_PATTERN.search(logical):
                return True

        return False