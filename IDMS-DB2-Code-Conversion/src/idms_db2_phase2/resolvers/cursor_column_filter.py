from __future__ import annotations

from idms_db2_phase2.resolvers.column_name_resolver import ColumnNameResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.timestamp_audit_rules import AUDIT_COLUMN_PREFIXES


class CursorColumnFilter:
    """
    Filters cursor columns to valid non-audit DB2 columns.

    This helper owns validation and de-duplication only.
    It does not choose business columns.
    """

    def __init__(
        self,
        table_name_resolver: TableNameResolver,
        column_name_resolver: ColumnNameResolver,
    ) -> None:
        self.table_name_resolver = table_name_resolver
        self.column_name_resolver = column_name_resolver

    def valid_non_audit_columns(
        self,
        record_name: str,
        columns: list[str],
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for column in columns:
            normalized = NameNormalizer.normalize(column)

            if not normalized:
                continue

            if normalized in seen:
                continue

            if self.is_audit_column(normalized):
                continue

            if not self.column_exists_for_record(record_name, normalized):
                continue

            seen.add(normalized)
            output.append(normalized)

        return output

    def column_exists_for_record(
        self,
        record_name: str,
        column_name: str,
    ) -> bool:
        table = self.table_name_resolver.table_for_record(record_name)

        if not table:
            return False

        return self.column_name_resolver.has_column(
            table_name=table,
            column_name=column_name,
        )

    def is_audit_column(
        self,
        column_name: str,
    ) -> bool:
        column = NameNormalizer.normalize(column_name)

        return any(
            column.startswith(prefix)
            for prefix in AUDIT_COLUMN_PREFIXES
        )

    def unique(
        self,
        values: list[str],
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for value in values:
            normalized = str(value or "").strip()

            if not normalized:
                continue

            key = NameNormalizer.normalize(normalized)

            if key in seen:
                continue

            seen.add(key)
            output.append(normalized)

        return output