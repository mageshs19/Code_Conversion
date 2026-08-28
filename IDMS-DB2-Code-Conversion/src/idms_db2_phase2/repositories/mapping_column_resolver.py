# LOCATION: src/idms_db2_phase2/repositories/mapping_column_resolver.py
# ACTION: CREATE NEW FILE

"""
Sheet Mapping column resolution.

Deterministic source-field -> DB2 column resolution using direct row
pairing (COBOL-side identifier -> new_db2_field_name), plus audit and
update-candidate column logic. No fuzzy / similarity matching.
"""

from __future__ import annotations

from idms_db2_phase2.repositories.mapping_key_resolver import (
    MappingKeyResolver,
)
from idms_db2_phase2.repositories.mapping_row_query import MappingRowQuery
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.field_naming_rules import (
    INSERT_ONLY_AUDIT_PREFIXES,
    UPDATE_AUDIT_PREFIXES,
    canonical_field_key,
)


class MappingColumnResolver:
    def __init__(
        self,
        query: MappingRowQuery,
        key_resolver: MappingKeyResolver,
    ) -> None:
        self.query = query
        self.key_resolver = key_resolver

    def column_for_source_field(
        self,
        record_name: str,
        source_field_name: str,
    ) -> str:
        """
        Resolve a COBOL source field to its DB2 column via the Sheet Mapping
        row directly. Each row pairs the COBOL-side identifier with the DB2
        column, so this is an exact canonical-key lookup. Deterministic only.
        """
        source_key = canonical_field_key(source_field_name)
        if not source_key:
            return ""

        for row in self.query.rows_for_record(record_name):
            column = NameNormalizer.normalize(
                row.new_db2_field_name or row.cross_application_db2_field_name
            )
            if not column:
                continue

            for candidate in (
                row.cobol_zone,
                row.reference_field_name_copybook,
                row.new_db2_field_name,
                row.cross_application_db2_field_name,
            ):
                if canonical_field_key(candidate) == source_key:
                    return column

        # No deterministic mapping found. Never guess.
        return ""

    def update_audit_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for row in self.query.rows_for_record(record_name):
            column = NameNormalizer.normalize(row.new_db2_field_name)
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

        return output

    def update_candidate_columns_for_record(
        self,
        record_name: str,
        changed_source_fields: list[str] | None = None,
    ) -> list[str]:
        """
        Return conservative UPDATE candidate columns.

        - Resolve changed source fields through Sheet Mapping to DB2 columns.
        - Exclude composite key columns.
        - Exclude TS_CREATE (insert-only).
        - Add update audit columns only if present in Sheet Mapping.
        - Do not invent DB2 columns.
        """
        output: list[str] = []
        seen: set[str] = set()

        key_columns = set(
            self.key_resolver.primary_key_columns_for_record(record_name)
        )

        for source_field in changed_source_fields or []:
            column = NameNormalizer.normalize(
                self.column_for_source_field(
                    record_name=record_name,
                    source_field_name=source_field,
                )
            )
            if not column:
                continue
            if column in key_columns:
                continue
            if column.startswith(INSERT_ONLY_AUDIT_PREFIXES):
                continue
            if column in seen:
                continue
            seen.add(column)
            output.append(column)

        for column in self.update_audit_columns_for_record(record_name):
            column = NameNormalizer.normalize(column)
            if not column or column in key_columns or column in seen:
                continue
            seen.add(column)
            output.append(column)

        return output