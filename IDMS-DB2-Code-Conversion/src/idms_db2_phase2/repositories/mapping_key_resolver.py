# LOCATION: src/idms_db2_phase2/repositories/mapping_key_resolver.py
# ACTION: CREATE NEW FILE

"""
Sheet Mapping key-column resolution.

Deterministic primary / foreign / non-key column logic.
"""

from __future__ import annotations

from idms_db2_phase2.repositories.mapping_row_query import MappingRowQuery
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class MappingKeyResolver:
    def __init__(
        self,
        query: MappingRowQuery,
    ) -> None:
        self.query = query

    def primary_key_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        """
        Return all primary-key-style columns for DB2 WHERE clauses.

        - If key is composite, include all mandatory PK / CALC key fields.
        - Never include FK / FOREIGN / relationship fields.
        - Preserve Sheet Mapping order.
        - Do not return duplicate columns.
        """
        output: list[str] = []
        seen: set[str] = set()

        for row in self.query.rows_for_record(record_name):
            idms_key = NameNormalizer.normalize(getattr(row, "idms_key", ""))
            db2_key = NameNormalizer.normalize(getattr(row, "db2_key", ""))
            relation = NameNormalizer.normalize(getattr(row, "relation", ""))
            column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
                or getattr(row, "cross_application_db2_field_name", "")
            )
            if not column:
                continue

            key_text = " ".join([idms_key, db2_key, relation])
            padded_key_text = f" {key_text} "

            if "FOREIGN" in key_text:
                continue
            if " FK " in padded_key_text:
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

    def foreign_key_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        """
        Return FK / FOREIGN / relationship columns for a record.

        Ensures FK fields are never treated as UPDATE / DELETE / SELECT
        WHERE identity keys.
        """
        output: list[str] = []
        seen: set[str] = set()

        for row in self.query.rows_for_record(record_name):
            db2_key = NameNormalizer.normalize(getattr(row, "db2_key", ""))
            relation = NameNormalizer.normalize(getattr(row, "relation", ""))
            text = " ".join([db2_key, relation])
            padded_text = f" {text} "

            is_foreign = "FOREIGN" in text or " FK " in padded_text
            if not is_foreign:
                continue

            column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
                or getattr(row, "cross_application_db2_field_name", "")
            )
            if not column or column in seen:
                continue

            seen.add(column)
            output.append(column)

        return output

    def non_key_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        key_columns = set(
            self.primary_key_columns_for_record(record_name)
        )
        output: list[str] = []
        seen: set[str] = set()

        for row in self.query.rows_for_record(record_name):
            column = NameNormalizer.normalize(row.new_db2_field_name)
            if not column or column in key_columns or column in seen:
                continue
            seen.add(column)
            output.append(column)

        return output