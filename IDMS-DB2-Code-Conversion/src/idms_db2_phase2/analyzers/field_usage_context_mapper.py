from __future__ import annotations

from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.field_usage_rules import DCLGEN_GROUP_PREFIX


class FieldUsageContextMapper:
    """
    Builds reusable record and DCLGEN-group context for field usage analysis.
    """

    def __init__(
        self,
        *,
        mapping_repository: MappingRepository,
        table_name_resolver: TableNameResolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.table_name_resolver = table_name_resolver

    def mapping_records(
        self,
    ) -> set[str]:
        try:
            return {
                NameNormalizer.normalize(record)
                for record in self.mapping_repository.records()
                if NameNormalizer.normalize(record)
            }
        except Exception:
            return set()

    def group_to_record_map(
        self,
    ) -> dict[str, str]:
        output: dict[str, str] = {}

        for record in self.mapping_records():
            normalized_record = NameNormalizer.normalize(record)
            table = self.table_name_resolver.table_for_record(normalized_record)

            if not table:
                continue

            group = DCLGEN_GROUP_PREFIX + NameNormalizer.to_cobol(table)
            output[NameNormalizer.normalize(group)] = normalized_record

        return output