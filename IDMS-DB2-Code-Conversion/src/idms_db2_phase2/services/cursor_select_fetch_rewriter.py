from __future__ import annotations

from idms_db2_phase2.services.cursor_select_column_parser import (
    CursorSelectColumnParser,
)
from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from patterns.final_feedback_fix_patterns import (
    END_EXEC_PATTERN,
    FROM_PATTERN,
    HOST_REFERENCE_PATTERN,
    SELECT_KEYWORD_PATTERN,
)
from rules.cursor_select_minimizer_rules import (
    FETCH_HOST_BODY_PREFIX,
    SELECT_FIRST_ITEM_BODY_PREFIX,
    SELECT_NEXT_ITEM_BODY_PREFIX,
)


class CursorSelectFetchRewriter:
    """
    Removes SELECT and FETCH INTO items by position and normalizes commas only
    within their respective scopes.
    """

    def __init__(
        self,
        *,
        fixed_format: FixedFormatLineService,
        column_parser: CursorSelectColumnParser,
    ) -> None:
        self.fixed_format = fixed_format
        self.column_parser = column_parser

    def remove_select_positions(
        self,
        block: list[str],
        positions: set[int],
    ) -> list[str]:
        output: list[str] = []
        in_select = False
        position = -1

        for line in block:
            logical = self.fixed_format.logical(line)

            if SELECT_KEYWORD_PATTERN.match(logical):
                in_select = True
                output.append(line)
                continue

            if in_select and FROM_PATTERN.search(logical):
                in_select = False
                output = self.normalize_select_commas(output)
                output.append(line)
                continue

            if in_select:
                column = self.column_parser.select_column_from_logical(logical)

                if column:
                    position += 1

                    if position in positions:
                        continue

            output.append(line)

        return self.normalize_select_commas(output)

    def remove_fetch_positions(
        self,
        block: list[str],
        positions: set[int],
    ) -> list[str]:
        output: list[str] = []
        in_into = False
        position = -1

        for line in block:
            logical = self.fixed_format.logical(line)

            if logical.upper() == "INTO":
                in_into = True
                output.append(line)
                continue

            if in_into and END_EXEC_PATTERN.search(logical):
                in_into = False
                output = self.normalize_fetch_commas(output)
                output.append(line)
                continue

            if in_into and HOST_REFERENCE_PATTERN.search(logical):
                position += 1

                if position in positions:
                    continue

            output.append(line)

        return self.normalize_fetch_commas(output)

    def normalize_select_commas(
        self,
        lines: list[str],
    ) -> list[str]:
        result = list(lines)
        indexes: list[int] = []
        in_select = False

        for index, line in enumerate(result):
            logical = self.fixed_format.logical(line)

            if SELECT_KEYWORD_PATTERN.match(logical):
                in_select = True
                continue

            if in_select and FROM_PATTERN.search(logical):
                break

            if not in_select:
                continue

            column = self.column_parser.select_column_from_logical(logical)

            if column:
                indexes.append(index)

        for item_number, line_index in enumerate(indexes):
            line = result[line_index]
            logical = self.fixed_format.logical(line)
            column = logical.lstrip(",").strip()

            if item_number == 0:
                body = f"{SELECT_FIRST_ITEM_BODY_PREFIX}{column}"
            else:
                body = f"{SELECT_NEXT_ITEM_BODY_PREFIX}{column}"

            result[line_index] = self.fixed_format.replace_body(line, body)

        return result

    def normalize_fetch_commas(
        self,
        lines: list[str],
    ) -> list[str]:
        result = list(lines)
        indexes: list[int] = []
        in_into = False

        for index, line in enumerate(result):
            logical = self.fixed_format.logical(line)

            if logical.upper() == "INTO":
                in_into = True
                continue

            if in_into and END_EXEC_PATTERN.search(logical):
                break

            if not in_into:
                continue

            if HOST_REFERENCE_PATTERN.search(logical):
                indexes.append(index)

        for item_number, line_index in enumerate(indexes):
            line = result[line_index]
            logical = self.fixed_format.logical(line).rstrip(",")

            if item_number < len(indexes) - 1:
                logical = logical + ","

            result[line_index] = self.fixed_format.replace_body(
                line,
                FETCH_HOST_BODY_PREFIX + logical,
            )

        return result