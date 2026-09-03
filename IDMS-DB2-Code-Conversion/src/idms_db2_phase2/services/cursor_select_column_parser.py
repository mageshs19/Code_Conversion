from __future__ import annotations

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from patterns.final_feedback_fix_patterns import (
    ASC_DESC_PATTERN,
    END_EXEC_PATTERN,
    FOR_READ_ONLY_PATTERN,
    FROM_PATTERN,
    ORDER_BY_PATTERN,
    SELECT_ITEM_PATTERN,
    SELECT_KEYWORD_PATTERN,
    SQL_NAME_TOKEN_PATTERN,
)
from rules.cursor_select_minimizer_rules import SQL_NON_COLUMN_KEYWORDS


class CursorSelectColumnParser:
    """
    Parses SELECT columns and ORDER BY columns from a DECLARE CURSOR block.

    This parser does not remove or rewrite lines.
    """

    def __init__(
        self,
        fixed_format: FixedFormatLineService,
    ) -> None:
        self.fixed_format = fixed_format

    def select_columns(
        self,
        block: list[str],
    ) -> list[str]:
        columns: list[str] = []
        in_select = False

        for line in block:
            logical = self.fixed_format.logical(line)

            if SELECT_KEYWORD_PATTERN.match(logical):
                in_select = True
                continue

            if in_select and FROM_PATTERN.search(logical):
                break

            if in_select:
                column = self.select_column_from_logical(logical)

                if column:
                    columns.append(column)

        return columns

    def select_column_from_logical(
        self,
        logical: str,
    ) -> str:
        text = str(logical or "").strip()

        if not text:
            return ""

        if self.is_sql_non_column_keyword(text):
            return ""

        match = SELECT_ITEM_PATTERN.match(text)

        if not match:
            return ""

        column = match.group("column").upper()

        if self.is_sql_non_column_keyword(column):
            return ""

        return column

    def order_by_columns(
        self,
        block: list[str],
    ) -> list[str]:
        columns: list[str] = []
        in_order_by = False

        for line in block:
            logical = self.fixed_format.logical(line)

            if ORDER_BY_PATTERN.search(logical):
                in_order_by = True
                remainder = ORDER_BY_PATTERN.sub("", logical).strip()

                if remainder:
                    columns.extend(self.parse_order_by_columns(remainder))

                continue

            if in_order_by:
                if FOR_READ_ONLY_PATTERN.search(logical) or END_EXEC_PATTERN.search(logical):
                    break

                columns.extend(self.parse_order_by_columns(logical))

        return columns

    def parse_order_by_columns(
        self,
        text: str,
    ) -> list[str]:
        columns: list[str] = []

        for item in str(text or "").split(","):
            token = item.strip()
            token = ASC_DESC_PATTERN.sub("", token).strip()
            token = token.strip(",")

            if SQL_NAME_TOKEN_PATTERN.match(token):
                columns.append(token.upper())

        return columns

    def is_sql_non_column_keyword(
        self,
        value: str,
    ) -> bool:
        text = str(value or "").strip().upper().lstrip(",").strip()
        return text in SQL_NON_COLUMN_KEYWORDS

    def normalize_name(
        self,
        value: str,
    ) -> str:
        return str(value or "").strip().upper().replace("-", "_")