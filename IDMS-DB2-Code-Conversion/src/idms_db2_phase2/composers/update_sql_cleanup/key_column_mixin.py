# LOCATION: src/idms_db2_phase2/composers/update_sql_cleanup/key_column_mixin.py
# ACTION: CREATE NEW FILE

"""Primary-key column resolution mixin for update-program SQL cleanup."""

from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.update_sql_cleanup_rules import IDENTITY_KEY_PREFIXES


class KeyColumnMixin:
    def _db2_primary_key_columns(
        self,
        record: str,
        table: str,
    ) -> list[str]:
        """
        Return DB2 primary-key columns for SQL WHERE.

        1. Use Sheet Mapping rows marked DB2 PRIMARY/KEY.
        2. Remove rows marked as foreign/relationship.
        3. If multiple primary columns exist and a DB2 identity-style key is
           present, narrow to identity-style keys.
        4. Otherwise fall back to repository key metadata.
        """
        strict_keys = self._strict_db2_primary_key_columns(record)
        strict_keys = self._filter_existing_dclgen_columns(table, strict_keys)

        if len(strict_keys) <= 1:
            return strict_keys

        identity_keys = [
            column
            for column in strict_keys
            if column.startswith(IDENTITY_KEY_PREFIXES)
        ]

        if identity_keys:
            return identity_keys

        return strict_keys

    def _strict_db2_primary_key_columns(
        self,
        record: str,
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for row in self.mapping_repository.rows_for_record(record):
            db2_key = NameNormalizer.normalize(getattr(row, "db2_key", ""))
            relation = NameNormalizer.normalize(getattr(row, "relation", ""))
            column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
            )

            if not column:
                continue
            if "FOREIGN" in relation:
                continue
            if "FOREIGN" in db2_key:
                continue
            if "PRIMARY" not in db2_key and db2_key != "KEY":
                continue
            if column in seen:
                continue

            seen.add(column)
            output.append(column)

        if output:
            return output

        if hasattr(self.mapping_repository, "key_columns_for_record"):
            return self.mapping_repository.key_columns_for_record(record)

        return []