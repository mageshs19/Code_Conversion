# LOCATION: src/idms_db2_phase2/generators/sql/sql_column_resolver.py
# ACTION: CREATE NEW FILE

"""SQL column resolution: table, key columns, insert columns, DCLGEN filter."""

from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.timestamp_audit_rules import INSERT_EXCLUDE_AUDIT_PREFIXES


class SqlColumnResolver:
    def __init__(
        self,
        mapping_repository,
        dclgen_repository,
        table_name_resolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.dclgen_repository = dclgen_repository
        self.table_name_resolver = table_name_resolver

    def resolved_table_for_record(self, record_name: str) -> str:
        mapped_table = self.mapping_repository.db2_table_for_record(
            record_name
        )
        if not mapped_table:
            return ""
        return self.table_name_resolver.resolve_table(mapped_table)

    def key_columns_for_record(
        self,
        record_name: str,
        table_name: str,
    ) -> list[str]:
        """
        Key columns for SQL WHERE. Composite PK / CALC keys required; FK /
        FOREIGN columns never included; Sheet Mapping order preserved.
        """
        columns: list[str] = []

        if hasattr(self.mapping_repository, "rows_for_record"):
            columns = self._key_columns_from_mapping_rows(record_name)

        if not columns and hasattr(
            self.mapping_repository,
            "primary_key_columns_for_record",
        ):
            columns = self.mapping_repository.primary_key_columns_for_record(
                record_name
            )

        return self.filter_to_existing_dclgen_columns(
            table_name=table_name,
            columns=columns,
        )

    def _key_columns_from_mapping_rows(
        self,
        record_name: str,
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for row in self.mapping_repository.rows_for_record(record_name):
            idms_key = NameNormalizer.normalize(getattr(row, "idms_key", ""))
            db2_key = NameNormalizer.normalize(getattr(row, "db2_key", ""))
            relation = NameNormalizer.normalize(getattr(row, "relation", ""))
            column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
                or getattr(row, "cross_application_db2_field_name", "")
            )
            if not column:
                continue

            combined_text = " ".join([idms_key, db2_key, relation])
            padded_text = f" {combined_text} "

            if "FOREIGN" in combined_text:
                continue
            if " FK " in padded_text:
                continue

            is_key_column = (
                "PRIMARY" in db2_key
                or db2_key == "KEY"
                or "PRIMARY" in idms_key
                or idms_key == "KEY"
                or "CALC" in idms_key
            )
            if not is_key_column:
                continue
            if column in seen:
                continue

            seen.add(column)
            output.append(column)

        return output

    def insert_columns_for_record(
        self,
        record_name: str,
        table_name: str,
    ) -> list[str]:
        columns = self.mapping_repository.db2_columns_for_table(table_name)
        columns = [
            column
            for column in columns
            if not self._is_insert_excluded_audit_column(column)
        ]
        return self.filter_to_existing_dclgen_columns(table_name, columns)

    def minimal_select_columns(
        self,
        record_name: str,
        table_name: str,
        key_columns: list[str],
    ) -> list[str]:
        return self.filter_to_existing_dclgen_columns(
            table_name=table_name,
            columns=key_columns,
        )

    def filter_to_existing_dclgen_columns(
        self,
        table_name: str,
        columns: list[str],
    ) -> list[str]:
        resolved_table = self.table_name_resolver.resolve_table(table_name)
        if not resolved_table:
            return []

        dclgen_columns = set(
            self.dclgen_repository.column_names_for_table(resolved_table)
        )
        if not dclgen_columns:
            return []

        output: list[str] = []
        for column in columns:
            normalized = NameNormalizer.normalize(column)
            if not normalized:
                continue
            if normalized not in dclgen_columns:
                continue
            output.append(normalized)

        return self._unique(output)

    def _is_insert_excluded_audit_column(self, column_name: str) -> bool:
        column = NameNormalizer.normalize(column_name)
        return any(
            column.startswith(prefix)
            for prefix in INSERT_EXCLUDE_AUDIT_PREFIXES
        )

    def _unique(self, values: list[str]) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = NameNormalizer.normalize(value)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            output.append(normalized)
        return output