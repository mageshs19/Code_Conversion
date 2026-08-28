# LOCATION: src/idms_db2_phase2/composers/update_sql_cleanup/scan_mixin.py
# ACTION: CREATE NEW FILE

"""Line/text helpers, block-scan helpers, and predicates."""

from __future__ import annotations

from idms_db2_phase2.composers.update_sql_cleanup.update_sql_cleanup_patterns import (
    END_IF_PATTERN,
    EXEC_SQL_END_PATTERN,
)
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.sequence_patterns import strip_sequence_numbers
from rules.update_sql_cleanup_rules import PROTECTED_BARE_TARGET_PREFIXES

from idms_db2_phase2.composers.update_sql_cleanup.update_sql_cleanup_patterns import (
    END_EVALUATE_PATTERN,
    END_IF_PATTERN,
    EXEC_SQL_END_PATTERN,
    LONE_PERIOD_PATTERN,
)


class ScanMixin:
    def _logical(
        self,
        line: str,
    ) -> str:
        return strip_sequence_numbers(str(line or "")).strip()

    def _leading_spaces(
        self,
        line: str,
    ) -> str:
        value = str(line or "")
        return value[: len(value) - len(value.lstrip())]

    def _table_for_record(
        self,
        record: str,
    ) -> str:
        mapped_table = self.mapping_repository.db2_table_for_record(record)
        if not mapped_table:
            return ""
        return self.table_name_resolver.resolve_table(mapped_table)

    def _is_protected_bare_target(
        self,
        target: str,
    ) -> bool:
        clean = NameNormalizer.to_cobol(target).upper()
        return clean.startswith(PROTECTED_BARE_TARGET_PREFIXES)

    def _skip_exec_sql(
        self,
        lines: list[str],
        index: int,
    ) -> int:
        while index < len(lines):
            logical = self._logical(lines[index])
            index += 1
            if EXEC_SQL_END_PATTERN.match(logical):
                break
        return index

    def _skip_if_block(
        self,
        lines: list[str],
        index: int,
    ) -> int:
        while index < len(lines):
            logical = self._logical(lines[index])
            index += 1
            if END_IF_PATTERN.match(logical):
                break
        return index
    # ADD this method inside class ScanMixin (next to _skip_if_block):

    def _skip_evaluate_block(
        self,
        lines: list[str],
        index: int,
    ) -> int:
        """
        Skip an EVALUATE SQLCODE ... END-EVALUATE block, including a trailing
        lone period line (the COBOL scope terminator emitted after
        END-EVALUATE).
        """
        while index < len(lines):
            logical = self._logical(lines[index])
            index += 1
            if END_EVALUATE_PATTERN.match(logical):
                break

        # Consume a following lone period line if present.
        while index < len(lines):
            logical = self._logical(lines[index])
            if not logical:
                index += 1
                continue
            if LONE_PERIOD_PATTERN.match(logical):
                index += 1
            break

        return index