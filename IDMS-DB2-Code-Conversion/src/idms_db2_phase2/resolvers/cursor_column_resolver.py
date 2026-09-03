from __future__ import annotations

from idms_db2_phase2.analyzers.field_usage_analyzer import FieldUsageAnalysis
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.column_name_resolver import ColumnNameResolver
from idms_db2_phase2.resolvers.cursor_column_filter import CursorColumnFilter
from idms_db2_phase2.resolvers.cursor_field_usage_column_selector import (
    CursorFieldUsageColumnSelector,
)
from idms_db2_phase2.resolvers.cursor_order_by_resolver import CursorOrderByResolver
from idms_db2_phase2.resolvers.relationship_resolver import RelationshipResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class CursorColumnResolver:
    """
    Resolves minimal cursor SELECT and ORDER BY columns generically.

    SELECT priority:
    1. DCLGEN host fields used in procedure logic.
    2. Fields used in procedure conditions.
    3. Fields used as MOVE sources for output writes.
    4. Parent key columns required by child cursor relationships.
    5. Child order key columns.
    6. Fallback to mapped non-audit columns only if usage is unavailable.

    ORDER BY rule:
    - Parent/root cursors do not get ORDER BY unless explicit order metadata
      exists in Sheet Mapping.
    - Child cursors may order by non-FK primary/sequence key.
    - DESC is added for child sequence/order key where metadata indicates
      sequence/event/latest-first semantics.
    """

    def __init__(
        self,
        mapping_repository: MappingRepository,
        table_name_resolver: TableNameResolver,
        column_name_resolver: ColumnNameResolver,
        relationship_resolver: RelationshipResolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.table_name_resolver = table_name_resolver
        self.column_name_resolver = column_name_resolver
        self.relationship_resolver = relationship_resolver

        self.column_filter = CursorColumnFilter(
            table_name_resolver=table_name_resolver,
            column_name_resolver=column_name_resolver,
        )
        self.usage_column_selector = CursorFieldUsageColumnSelector(
            mapping_repository=mapping_repository,
        )
        self.order_by_resolver = CursorOrderByResolver(
            mapping_repository=mapping_repository,
            relationship_resolver=relationship_resolver,
            column_filter=self.column_filter,
        )

    def select_columns_for_record(
        self,
        record_name: str,
        field_usage_analysis: FieldUsageAnalysis | None = None,
    ) -> list[str]:
        record = NameNormalizer.normalize(record_name)

        if not record:
            return []

        selected: list[str] = []

        selected.extend(
            self.usage_column_selector.columns_from_field_usage(
                record_name=record,
                field_usage_analysis=field_usage_analysis,
            )
        )

        selected.extend(
            self.relationship_resolver.parent_key_columns_required_by_children(record)
        )

        if self.relationship_resolver.has_foreign_keys(record):
            selected.extend(
                self.order_by_resolver.order_by_base_columns_for_record(record)
            )

        selected = self.column_filter.valid_non_audit_columns(
            record_name=record,
            columns=selected,
        )

        if selected:
            return selected

        fallback = self.column_name_resolver.columns_for_record(record)

        return self.column_filter.valid_non_audit_columns(
            record_name=record,
            columns=fallback,
        )

    def order_by_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        return self.order_by_resolver.order_by_columns_for_record(record_name)