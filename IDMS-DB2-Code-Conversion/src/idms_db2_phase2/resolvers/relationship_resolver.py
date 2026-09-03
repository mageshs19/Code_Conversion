from __future__ import annotations

from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.relationship_child_resolver import (
    RelationshipChildResolver,
)
from idms_db2_phase2.resolvers.relationship_key_classifier import (
    RelationshipKeyClassifier,
)
from idms_db2_phase2.resolvers.relationship_key_column_resolver import (
    RelationshipKeyColumnResolver,
)
from idms_db2_phase2.resolvers.relationship_models import (
    RelationshipCondition,
    RelationshipResolution,
)
from idms_db2_phase2.resolvers.relationship_table_lookup import RelationshipTableLookup
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class RelationshipResolver:
    """
    Resolves parent-child DB2 relationships using Sheet Mapping metadata.

    Public facade preserved for existing callers.
    """

    def __init__(
        self,
        mapping_repository: MappingRepository,
        table_name_resolver: TableNameResolver,
        host_variable_resolver: HostVariableResolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.table_name_resolver = table_name_resolver
        self.host_variable_resolver = host_variable_resolver

        self.classifier = RelationshipKeyClassifier()
        self.key_column_resolver = RelationshipKeyColumnResolver(
            mapping_repository=mapping_repository,
            classifier=self.classifier,
        )
        self.table_lookup = RelationshipTableLookup(
            mapping_repository=mapping_repository,
            table_name_resolver=table_name_resolver,
        )
        self.child_resolver = RelationshipChildResolver(
            mapping_repository=mapping_repository,
            table_name_resolver=table_name_resolver,
            host_variable_resolver=host_variable_resolver,
            key_column_resolver=self.key_column_resolver,
            table_lookup=self.table_lookup,
            classifier=self.classifier,
        )

    def resolve_for_child_record(
        self,
        child_record: str,
    ) -> RelationshipResolution:
        return self.child_resolver.resolve_for_child_record(child_record)

    def foreign_key_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        return self.key_column_resolver.foreign_key_columns_for_record(record_name)

    def primary_key_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        return self.key_column_resolver.primary_key_columns_for_record(record_name)

    def parent_key_columns_required_by_children(
        self,
        parent_record: str,
    ) -> list[str]:
        parent = NameNormalizer.normalize(parent_record)
        output: list[str] = []
        seen: set[str] = set()

        for child in self.mapping_repository.records():
            child = NameNormalizer.normalize(child)

            if child == parent:
                continue

            relation = self.resolve_for_child_record(child)

            if relation.parent_record != parent:
                continue

            for condition in relation.conditions:
                column = NameNormalizer.normalize(condition.parent_column)

                if not column or column in seen:
                    continue

                seen.add(column)
                output.append(column)

        return output

    def order_by_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        return self.key_column_resolver.order_by_columns_for_record(record_name)

    def has_foreign_keys(
        self,
        record_name: str,
    ) -> bool:
        return self.key_column_resolver.has_foreign_keys(record_name)


__all__ = [
    "RelationshipCondition",
    "RelationshipResolution",
    "RelationshipResolver",
]