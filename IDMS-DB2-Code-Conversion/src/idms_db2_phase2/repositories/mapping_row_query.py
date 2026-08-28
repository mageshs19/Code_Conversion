# LOCATION: src/idms_db2_phase2/repositories/mapping_row_query.py
# ACTION: CREATE NEW FILE

"""
Sheet Mapping row query helpers.

Pure row filtering / listing. No column or key resolution logic.
"""

from __future__ import annotations

from idms_db2_phase2.domain.models import SheetMappingRow
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class MappingRowQuery:
    def __init__(
        self,
        rows: list[SheetMappingRow],
    ) -> None:
        self.rows = rows

    def all(self) -> list[SheetMappingRow]:
        return list(self.rows)

    def count(self) -> int:
        return len(self.rows)

    def records(self) -> list[str]:
        values = {
            NameNormalizer.normalize(row.cobol_record_idms)
            for row in self.rows
            if NameNormalizer.normalize(row.cobol_record_idms)
        }
        return sorted(values)

    def tables(self) -> list[str]:
        values = {
            NameNormalizer.normalize(
                row.new_db2_record or row.cross_application_db2_table
            )
            for row in self.rows
            if NameNormalizer.normalize(
                row.new_db2_record or row.cross_application_db2_table
            )
        }
        return sorted(values)

    def rows_for_record(
        self,
        record_name: str,
    ) -> list[SheetMappingRow]:
        target = NameNormalizer.normalize(record_name)

        if not target:
            return []

        return [
            row
            for row in self.rows
            if NameNormalizer.normalize(row.cobol_record_idms) == target
        ]

    def rows_for_table(
        self,
        table_name: str,
    ) -> list[SheetMappingRow]:
        target = NameNormalizer.normalize(table_name)

        if not target:
            return []

        return [
            row
            for row in self.rows
            if NameNormalizer.normalize(row.new_db2_record) == target
            or NameNormalizer.normalize(row.cross_application_db2_table)
            == target
        ]

    def db2_columns_for_table(
        self,
        table_name: str,
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for row in self.rows_for_table(table_name):
            column = NameNormalizer.normalize(
                row.new_db2_field_name or row.cross_application_db2_field_name
            )
            if not column or column in seen:
                continue
            seen.add(column)
            output.append(column)

        return output

    def db2_table_for_record(
        self,
        record_name: str,
    ) -> str:
        rows = self.rows_for_record(record_name)

        for row in rows:
            table = NameNormalizer.normalize(row.new_db2_record)
            if table:
                return table

        for row in rows:
            table = NameNormalizer.normalize(row.cross_application_db2_table)
            if table:
                return table

        return ""