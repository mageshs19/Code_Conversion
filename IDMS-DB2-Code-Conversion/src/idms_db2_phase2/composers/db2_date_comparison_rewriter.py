"""
DB2 date comparison rewriter.

Rewrites each detected IF date comparison (DB2 date host field vs PARMDATE)
into safe realignment + conversion logic followed by the rewritten IF.

Rewriting logic only. Templates live in rules/db2_date_conversion_rules.py;
regex lives in patterns/db2_date_patterns.py.
"""

from idms_db2_phase2.composers.db2_date_line_utils import Db2DateLineUtils
from patterns.db2_date_patterns import DB2_DATE_COMPARISON_PATTERN
from rules.db2_date_conversion_rules import (
    DB2_DATE_CONVERSION_LINE_TEMPLATES,
    DB2_DATE_HIGH_NUMERIC_LITERAL,
    DB2_DATE_HIGH_VALUE_LITERAL,
    DB2_DATE_IF_REPLACEMENT_TEMPLATE,
    DB2_DATE_LOW_VALUE_LITERAL,
)

DEFAULT_INDENT = "    "


class Db2DateComparisonRewriter:
    def __init__(
        self,
        line_utils: Db2DateLineUtils | None = None,
    ) -> None:
        self.line_utils = line_utils or Db2DateLineUtils()

    def rewrite_date_comparisons(self, lines: list[str]) -> list[str]:
        output: list[str] = []

        for line in lines:
            logical = self.line_utils.logical(line)

            if self.line_utils.is_comment_or_blank(logical):
                output.append(line)
                continue

            match = DB2_DATE_COMPARISON_PATTERN.match(logical)

            if not match:
                output.append(line)
                continue

            field_name = self.line_utils.clean_cobol_name(match.group("field"))
            group_name = self.line_utils.clean_cobol_name(match.group("group"))
            condition = str(match.group("condition") or "").strip()

            if not field_name or not group_name or not condition:
                output.append(line)
                continue

            indent = self.line_utils.leading_spaces_from_line(
                line=line,
                default=DEFAULT_INDENT,
            )

            output.extend(
                self._date_conversion_lines(
                    indent=indent,
                    field_name=field_name,
                    group_name=group_name,
                )
            )
            output.append(
                self._replace_date_field_in_if(
                    indent=indent,
                    field_name=field_name,
                    condition=condition,
                )
            )

        return output

    def _date_conversion_lines(
        self,
        indent: str,
        field_name: str,
        group_name: str,
    ) -> list[str]:
        helper = self.line_utils.helper_name(field_name)

        output: list[str] = []

        for template in DB2_DATE_CONVERSION_LINE_TEMPLATES:
            output.append(
                template.format(
                    indent=indent,
                    field_name=field_name,
                    group_name=group_name,
                    helper=helper,
                    low_value=DB2_DATE_LOW_VALUE_LITERAL,
                    high_value=DB2_DATE_HIGH_VALUE_LITERAL,
                    high_numeric=DB2_DATE_HIGH_NUMERIC_LITERAL,
                )
            )

        return output

    def _replace_date_field_in_if(
        self,
        indent: str,
        field_name: str,
        condition: str,
    ) -> str:
        helper = self.line_utils.helper_name(field_name)

        return DB2_DATE_IF_REPLACEMENT_TEMPLATE.format(
            indent=indent,
            helper=helper,
            condition=condition,
        )