from __future__ import annotations

from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class RelationshipTableLookup:
    """
    Resolves records from DB2 tables and parent tables from key columns.
    """

    def __init__(
        self,
        *,
        mapping_repository: MappingRepository,
        table_name_resolver: TableNameResolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.table_name_resolver = table_name_resolver

    def record_for_table(
        self,
        table_name: str,
    ) -> str:
        table = self.table_name_resolver.resolve_table(table_name)

        if not table:
            return ""

        for record in self.mapping_repository.records():
            record_table = self.table_name_resolver.table_for_record(record)

            if record_table == table:
                return NameNormalizer.normalize(record)

        return ""

    def find_parent_table_by_column(
        self,
        *,
        child_record: str,
        child_column: str,
        primary_key_columns_for_record,
    ) -> str:
        column = NameNormalizer.normalize(child_column)

        if not column:
            return ""

        child_table = self.table_name_resolver.table_for_record(child_record)

        for record in self.mapping_repository.records():
            normalized_record = NameNormalizer.normalize(record)

            if normalized_record == child_record:
                continue

            table = self.table_name_resolver.table_for_record(normalized_record)

            if not table:
                continue

            if table == child_table:
                continue

            if column in primary_key_columns_for_record(normalized_record):
                return table

        return ""