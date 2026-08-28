# LOCATION: src/idms_db2_phase2/repositories/mapping_repository.py
# ACTION: REPLACE ENTIRE FILE

"""
Repository wrapper for Sheet Mapping rows.

Authority:
- Sheet Mapping provides DB2 record/table names and column names.
- Source-field resolution is deterministic (COBOL identifier ->
  new_db2_field_name on the same row). No fuzzy / similarity matching.

This class is a thin facade that delegates to focused helpers:
- MappingRowQuery       (row filtering / listing)
- MappingKeyResolver    (primary / foreign / non-key columns)
- MappingColumnResolver (source->column, audit, update candidates)
"""

from __future__ import annotations

from idms_db2_phase2.domain.models import SheetMappingRow
from idms_db2_phase2.repositories.mapping_column_resolver import (
    MappingColumnResolver,
)
from idms_db2_phase2.repositories.mapping_key_resolver import (
    MappingKeyResolver,
)
from idms_db2_phase2.repositories.mapping_row_query import MappingRowQuery


class MappingRepository:
    def __init__(
        self,
        rows: list[SheetMappingRow] | None = None,
    ) -> None:
        self.rows = rows or []
        self._query = MappingRowQuery(self.rows)
        self._keys = MappingKeyResolver(self._query)
        self._columns = MappingColumnResolver(self._query, self._keys)

    # --- row query ---
    def all(self) -> list[SheetMappingRow]:
        return self._query.all()

    def count(self) -> int:
        return self._query.count()

    def records(self) -> list[str]:
        return self._query.records()

    def tables(self) -> list[str]:
        return self._query.tables()

    def rows_for_record(
        self,
        record_name: str,
    ) -> list[SheetMappingRow]:
        return self._query.rows_for_record(record_name)

    def rows_for_table(
        self,
        table_name: str,
    ) -> list[SheetMappingRow]:
        return self._query.rows_for_table(table_name)

    def db2_columns_for_table(
        self,
        table_name: str,
    ) -> list[str]:
        return self._query.db2_columns_for_table(table_name)

    def db2_table_for_record(
        self,
        record_name: str,
    ) -> str:
        return self._query.db2_table_for_record(record_name)

    def has_record(self, record_name: str) -> bool:
        return bool(self._query.rows_for_record(record_name))

    def has_table(self, table_name: str) -> bool:
        return bool(self._query.rows_for_table(table_name))

    # --- key resolution ---
    def key_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        return self._keys.primary_key_columns_for_record(record_name)

    def primary_key_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        return self._keys.primary_key_columns_for_record(record_name)

    def foreign_key_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        return self._keys.foreign_key_columns_for_record(record_name)

    def non_key_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        return self._keys.non_key_columns_for_record(record_name)

    # --- column resolution ---
    def column_for_source_field(
        self,
        record_name: str,
        source_field_name: str,
    ) -> str:
        return self._columns.column_for_source_field(
            record_name=record_name,
            source_field_name=source_field_name,
        )

    def update_audit_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        return self._columns.update_audit_columns_for_record(record_name)

    def update_candidate_columns_for_record(
        self,
        record_name: str,
        changed_source_fields: list[str] | None = None,
    ) -> list[str]:
        return self._columns.update_candidate_columns_for_record(
            record_name=record_name,
            changed_source_fields=changed_source_fields,
        )