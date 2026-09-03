from __future__ import annotations

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from patterns.final_feedback_fix_patterns import (
    DECLARE_CURSOR_PATTERN,
    END_EXEC_PATTERN,
    FETCH_CURSOR_PATTERN,
)


class CursorSqlBlockScanner:
    """
    Finds DECLARE CURSOR and FETCH cursor EXEC SQL blocks.

    This scanner does not parse SELECT columns or rewrite SQL.
    """

    def __init__(
        self,
        fixed_format: FixedFormatLineService,
    ) -> None:
        self.fixed_format = fixed_format

    def find_declare_blocks(
        self,
        lines: list[str],
    ) -> list[tuple[str, int, int]]:
        blocks: list[tuple[str, int, int]] = []
        in_exec_sql = False
        start = -1
        cursor = ""

        for index, line in enumerate(lines):
            logical = self.fixed_format.logical(line)

            if logical.upper().startswith("EXEC SQL"):
                in_exec_sql = True
                start = index
                cursor = ""
                continue

            if in_exec_sql and not cursor:
                match = DECLARE_CURSOR_PATTERN.search(logical)

                if match:
                    cursor = match.group("cursor").upper()

            if in_exec_sql and END_EXEC_PATTERN.search(logical):
                if cursor:
                    blocks.append((cursor, start, index))

                in_exec_sql = False
                start = -1
                cursor = ""

        return blocks

    def find_fetch_blocks(
        self,
        lines: list[str],
    ) -> list[tuple[str, int, int]]:
        blocks: list[tuple[str, int, int]] = []
        in_exec_sql = False
        start = -1
        cursor = ""

        for index, line in enumerate(lines):
            logical = self.fixed_format.logical(line)

            if logical.upper().startswith("EXEC SQL"):
                in_exec_sql = True
                start = index
                cursor = ""
                continue

            if in_exec_sql and not cursor:
                match = FETCH_CURSOR_PATTERN.search(logical)

                if match:
                    cursor = match.group("cursor").upper()

            if in_exec_sql and END_EXEC_PATTERN.search(logical):
                if cursor:
                    blocks.append((cursor, start, index))

                in_exec_sql = False
                start = -1
                cursor = ""

        return blocks