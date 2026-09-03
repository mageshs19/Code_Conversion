"""
Cursor SELECT minimizer service.

Generic behavior:
- Removes columns selected/fetched only for ORDER BY when safe.
- Does not hardcode cursor names, table names, columns, or host variables.
- Keeps SELECT and FETCH INTO synchronized by position.

Important:
- Comma normalization is scoped only to SELECT item lines between SELECT and FROM.
- FETCH comma normalization is scoped only to host variables between INTO and END-EXEC.
- SQL keywords such as WHERE, FROM, ORDER BY, and FOR READ ONLY are never
  treated as selected columns.
"""

from __future__ import annotations

from idms_db2_phase2.services.cursor_select_column_parser import (
    CursorSelectColumnParser,
)
from idms_db2_phase2.services.cursor_select_fetch_rewriter import (
    CursorSelectFetchRewriter,
)
from idms_db2_phase2.services.cursor_select_usage_guard import (
    CursorSelectUsageGuard,
)
from idms_db2_phase2.services.cursor_sql_block_scanner import CursorSqlBlockScanner
from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from rules.final_feedback_fix_rules import ORDER_BY_COLUMNS_IN_SELECT_DEFAULT


class CursorSelectMinimizerService:
    """
    Removes order-by-only columns from cursor SELECT/FETCH when safe.

    Safety:
    - If the SQL column appears elsewhere outside the cursor declare block,
      keep it.
    - If the host-like COBOL name appears elsewhere outside the matching fetch
      block, keep it.
    - SELECT and FETCH are modified by position only when both are structurally
      safe.
    """

    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
        require_order_by_columns_in_select: bool = ORDER_BY_COLUMNS_IN_SELECT_DEFAULT,
    ) -> None:
        self.fixed_format = fixed_format or FixedFormatLineService()
        self.require_order_by_columns_in_select = require_order_by_columns_in_select

        self.block_scanner = CursorSqlBlockScanner(self.fixed_format)
        self.column_parser = CursorSelectColumnParser(self.fixed_format)
        self.usage_guard = CursorSelectUsageGuard(self.fixed_format)
        self.rewriter = CursorSelectFetchRewriter(
            fixed_format=self.fixed_format,
            column_parser=self.column_parser,
        )

    def minimize(
        self,
        text: str,
    ) -> str:
        source = str(text or "")

        if not source:
            return ""

        if self.require_order_by_columns_in_select:
            return source

        lines = source.splitlines()
        declare_blocks = self.block_scanner.find_declare_blocks(lines)
        fetch_blocks = self.block_scanner.find_fetch_blocks(lines)

        removals_by_cursor = self._removal_positions_by_cursor(
            lines=lines,
            declare_blocks=declare_blocks,
            fetch_blocks=fetch_blocks,
        )

        if not removals_by_cursor:
            return source

        updated = self._apply_select_removals(
            lines=lines,
            declare_blocks=declare_blocks,
            removals_by_cursor=removals_by_cursor,
        )

        fetch_blocks = self.block_scanner.find_fetch_blocks(updated)

        updated = self._apply_fetch_removals(
            lines=updated,
            fetch_blocks=fetch_blocks,
            removals_by_cursor=removals_by_cursor,
        )

        return "\n".join(updated)

    def _removal_positions_by_cursor(
        self,
        *,
        lines: list[str],
        declare_blocks: list[tuple[str, int, int]],
        fetch_blocks: list[tuple[str, int, int]],
    ) -> dict[str, set[int]]:
        removals_by_cursor: dict[str, set[int]] = {}

        for cursor, start, end in declare_blocks:
            block = lines[start : end + 1]
            select_columns = self.column_parser.select_columns(block)
            order_columns = self.column_parser.order_by_columns(block)

            if not select_columns or not order_columns:
                continue

            order_set = {
                self.column_parser.normalize_name(item)
                for item in order_columns
            }
            removable: set[int] = set()

            for index, column in enumerate(select_columns):
                if self.column_parser.normalize_name(column) not in order_set:
                    continue

                if self.usage_guard.has_non_order_usage(
                    lines=lines,
                    declare_range=(start, end),
                    fetch_blocks=fetch_blocks,
                    cursor=cursor,
                    column=column,
                ):
                    continue

                removable.add(index)

            if removable:
                removals_by_cursor[cursor] = removable

        return removals_by_cursor

    def _apply_select_removals(
        self,
        *,
        lines: list[str],
        declare_blocks: list[tuple[str, int, int]],
        removals_by_cursor: dict[str, set[int]],
    ) -> list[str]:
        updated = list(lines)

        for cursor, start, end in sorted(
            declare_blocks,
            key=lambda item: item[1],
            reverse=True,
        ):
            removable = removals_by_cursor.get(cursor)

            if not removable:
                continue

            block = updated[start : end + 1]
            updated[start : end + 1] = self.rewriter.remove_select_positions(
                block,
                removable,
            )

        return updated

    def _apply_fetch_removals(
        self,
        *,
        lines: list[str],
        fetch_blocks: list[tuple[str, int, int]],
        removals_by_cursor: dict[str, set[int]],
    ) -> list[str]:
        updated = list(lines)

        for cursor, start, end in sorted(
            fetch_blocks,
            key=lambda item: item[1],
            reverse=True,
        ):
            removable = removals_by_cursor.get(cursor)

            if not removable:
                continue

            block = updated[start : end + 1]
            updated[start : end + 1] = self.rewriter.remove_fetch_positions(
                block,
                removable,
            )

        return updated