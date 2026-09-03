from __future__ import annotations

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)


class CursorSelectUsageGuard:
    """
    Checks whether a candidate removable SELECT column is used outside its
    DECLARE CURSOR block and matching FETCH block.
    """

    def __init__(
        self,
        fixed_format: FixedFormatLineService,
    ) -> None:
        self.fixed_format = fixed_format

    def has_non_order_usage(
        self,
        *,
        lines: list[str],
        declare_range: tuple[int, int],
        fetch_blocks: list[tuple[str, int, int]],
        cursor: str,
        column: str,
    ) -> bool:
        host_like = column.replace("_", "-").upper()
        column_upper = column.upper()

        fetch_range = self.matching_fetch_range(fetch_blocks, cursor)

        for index, line in enumerate(lines):
            if self.index_in_range(index, declare_range):
                continue

            if fetch_range and self.index_in_range(index, fetch_range):
                continue

            logical = self.fixed_format.logical(line).upper()

            if column_upper in logical:
                return True

            if host_like in logical:
                return True

        return False

    def matching_fetch_range(
        self,
        fetch_blocks: list[tuple[str, int, int]],
        cursor: str,
    ) -> tuple[int, int] | None:
        for fetch_cursor, start, end in fetch_blocks:
            if fetch_cursor == cursor:
                return start, end

        return None

    def index_in_range(
        self,
        index: int,
        value_range: tuple[int, int],
    ) -> bool:
        start, end = value_range
        return start <= index <= end