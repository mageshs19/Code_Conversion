# LOCATION: src/idms_db2_phase2/composers/update_sql_cleanup/column_mixin.py
# ACTION: CREATE NEW FILE

"""
Column resolution mixin for update-program SQL cleanup.

Deterministic: delegates source-field -> DB2 column resolution to the
Sheet Mapping repository (the authority). No fuzzy / similarity matching.
"""

from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.update_sql_cleanup_rules import (
    INSERT_ONLY_AUDIT_PREFIXES,
    UPDATE_AUDIT_PREFIXES,
)


class ColumnMixin:
    def _column_for_source_field(
        self,
        record: str,
        source_field: str,
    ) -> str:
        """
        Resolve source field to DB2 column via the Sheet Mapping repository
        (deterministic authority). On no match, fail loud so a human corrects
        the mapping instead of the tool guessing.
        """
        column = self.mapping_repository.column_for_source_field(
            record_name=record,
            source_field_name=source_field,
        )

        if column:
            return NameNormalizer.normalize(column)

        self.messages.append(
            f"Mapping gap: source field '{source_field}' in record {record} "
            f"has no deterministic DB2 column. Manual mapping required."
        )
        return ""

    def _update_audit_columns(
        self,
        record: str,
        table: str,
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for row in self.mapping_repository.rows_for_record(record):
            column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
            )
            if not column:
                continue
            if column.startswith(INSERT_ONLY_AUDIT_PREFIXES):
                continue
            if not column.startswith(UPDATE_AUDIT_PREFIXES):
                continue
            if column in seen:
                continue
            seen.add(column)
            output.append(column)

        return self._filter_existing_dclgen_columns(table, output)

    def _filter_existing_dclgen_columns(
        self,
        table: str,
        columns: list[str],
    ) -> list[str]:
        valid_columns = set(
            self.dclgen_repository.column_names_for_table(table)
        )
        output: list[str] = []
        seen: set[str] = set()

        for column in columns:
            normalized = NameNormalizer.normalize(column)
            if not normalized:
                continue
            if normalized not in valid_columns:
                continue
            if normalized in seen:
                continue
            if not self.host_variable_resolver.has_host_for_column(
                table_name=table,
                column_name=normalized,
            ):
                continue
            seen.add(normalized)
            output.append(normalized)

        return output