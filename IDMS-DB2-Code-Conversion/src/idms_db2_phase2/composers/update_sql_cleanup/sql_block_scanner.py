# LOCATION: src/idms_db2_phase2/composers/update_sql_cleanup/sql_block_scanner.py
# ACTION: REPLACE ENTIRE FILE

"""
SQL block scanner.

Helpers to skip generated SQL / SQLCODE blocks and to find the next MODIFY
record marker. Uses the base class scan helpers via the owner instance.
"""

from __future__ import annotations

from idms_db2_phase2.composers.update_sql_cleanup.update_sql_cleanup_patterns import (
    SQLCODE_EVALUATE_PATTERN,
)
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class SqlBlockScanner:
    def __init__(self, owner) -> None:
        # owner exposes: _logical, _skip_exec_sql, _skip_if_block,
        # _skip_evaluate_block, EXEC_SQL_START_PATTERN, SQLCODE_IF_PATTERN,
        # CONVERTED_MODIFY_PATTERN
        self.owner = owner

    def next_modify_record(
        self,
        lines: list[str],
        start_index: int,
        max_distance: int,
    ) -> str:
        end = min(len(lines), start_index + max_distance + 1)
        for index in range(start_index + 1, end):
            logical = self.owner._logical(lines[index])
            match = self.owner.CONVERTED_MODIFY_PATTERN.match(logical)
            if match:
                return NameNormalizer.normalize(match.group("record"))
        return ""

    def skip_generated_sql_and_sqlcode(
        self,
        lines: list[str],
        start: int,
    ) -> int:
        index = start
        while index < len(lines):
            logical = self.owner._logical(lines[index])
            upper = logical.upper()

            if not logical:
                index += 1
                continue

            if upper.startswith("MOVE 'SELECT-") or upper.startswith(
                "MOVE 'UPDATE-"
            ):
                index += 1
                continue

            if self.owner.EXEC_SQL_START_PATTERN.match(logical):
                index = self.owner._skip_exec_sql(lines, index)
                continue

            # Skip an IF SQLCODE ... END-IF block.
            if self.owner.SQLCODE_IF_PATTERN.match(logical):
                index = self.owner._skip_if_block(lines, index)
                continue

            # Skip an EVALUATE SQLCODE ... END-EVALUATE block (+ period).
            if SQLCODE_EVALUATE_PATTERN.match(logical):
                index = self.owner._skip_evaluate_block(lines, index)
                continue

            break

        return index