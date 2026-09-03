from __future__ import annotations

from typing import Any

from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
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


class RelationshipChildResolver:
    """
    Resolves full parent-child relationship conditions for one child record.
    """

    def __init__(
        self,
        *,
        mapping_repository: MappingRepository,
        table_name_resolver: TableNameResolver,
        host_variable_resolver: HostVariableResolver,
        key_column_resolver: RelationshipKeyColumnResolver,
        table_lookup: RelationshipTableLookup,
        classifier: RelationshipKeyClassifier | None = None,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.table_name_resolver = table_name_resolver
        self.host_variable_resolver = host_variable_resolver
        self.key_column_resolver = key_column_resolver
        self.table_lookup = table_lookup
        self.classifier = classifier or RelationshipKeyClassifier()

    def resolve_for_child_record(
        self,
        child_record: str,
    ) -> RelationshipResolution:
        child = NameNormalizer.normalize(child_record)
        result = RelationshipResolution(child_record=child)

        if not child:
            result.diagnostics.append("Relationship resolver: child record is empty.")
            return result

        child_table = self.table_name_resolver.table_for_record(child)
        result.child_table = child_table

        rows = self.mapping_repository.rows_for_record(child)
        fk_rows = [
            row
            for row in rows
            if self.classifier.is_foreign_key_row(row)
        ]

        if not fk_rows:
            result.diagnostics.append(
                f"Relationship resolver: no foreign-key rows for child record {child}."
            )
            return result

        parent_record = self._infer_parent_record(
            child_record=child,
            fk_rows=fk_rows,
        )

        parent_table = ""

        if parent_record:
            parent_table = self.table_name_resolver.table_for_record(parent_record)

        result.parent_record = parent_record
        result.parent_table = parent_table

        self._append_conditions_from_fk_rows(
            result=result,
            child=child,
            child_table=child_table,
            fk_rows=fk_rows,
            parent_record=parent_record,
            parent_table=parent_table,
        )

        result.diagnostics.append(
            "Relationship resolver: "
            f"child={child}, parent={result.parent_record}, "
            f"conditions={len(result.conditions)}"
        )

        return result

    def _append_conditions_from_fk_rows(
        self,
        *,
        result: RelationshipResolution,
        child: str,
        child_table: str,
        fk_rows: list[Any],
        parent_record: str,
        parent_table: str,
    ) -> None:
        resolved_parent_record = parent_record

        for row in fk_rows:
            child_column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
                or getattr(row, "cross_application_db2_field_name", "")
            )

            if not child_column:
                continue

            explicit_parent_table = self.table_name_resolver.resolve_table(
                getattr(row, "cross_application_db2_table", "")
            )

            explicit_parent_column = NameNormalizer.normalize(
                getattr(row, "cross_application_db2_field_name", "")
            )

            effective_parent_table = explicit_parent_table or parent_table
            effective_parent_column = explicit_parent_column or child_column

            if not effective_parent_table:
                effective_parent_table = self.table_lookup.find_parent_table_by_column(
                    child_record=child,
                    child_column=child_column,
                    primary_key_columns_for_record=(
                        self.key_column_resolver.primary_key_columns_for_record
                    ),
                )

            if not effective_parent_table:
                result.diagnostics.append(
                    f"Relationship resolver: no parent table found for "
                    f"{child}.{child_column}."
                )
                continue

            if not resolved_parent_record:
                resolved_parent_record = self.table_lookup.record_for_table(
                    effective_parent_table
                )
                result.parent_record = resolved_parent_record

            if not result.parent_table:
                result.parent_table = effective_parent_table

            self._append_condition(
                result=result,
                child=child,
                child_table=child_table,
                child_column=child_column,
                parent_record=resolved_parent_record,
                parent_table=effective_parent_table,
                parent_column=effective_parent_column,
            )

    def _append_condition(
        self,
        *,
        result: RelationshipResolution,
        child: str,
        child_table: str,
        child_column: str,
        parent_record: str,
        parent_table: str,
        parent_column: str,
    ) -> None:
        parent_host = self.host_variable_resolver.host_reference_for_column(
            table_name=parent_table,
            column_name=parent_column,
        )

        if not parent_host:
            result.diagnostics.append(
                "Relationship resolver: missing parent host for "
                f"child={child}, child_column={child_column}, "
                f"parent_table={parent_table}, parent_column={parent_column}."
            )
            return

        result.conditions.append(
            RelationshipCondition(
                child_record=child,
                child_table=child_table,
                child_column=child_column,
                parent_record=parent_record,
                parent_table=parent_table,
                parent_column=parent_column,
                parent_host_reference=parent_host,
            )
        )

    def _infer_parent_record(
        self,
        *,
        child_record: str,
        fk_rows: list[Any],
    ) -> str:
        for row in fk_rows:
            parent_table = self.table_name_resolver.resolve_table(
                getattr(row, "cross_application_db2_table", "")
            )

            if parent_table:
                record = self.table_lookup.record_for_table(parent_table)
                if record:
                    return record

        best_record = ""
        best_count = 0

        child_fk_columns = {
            NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
                or getattr(row, "cross_application_db2_field_name", "")
            )
            for row in fk_rows
        }

        for record in self.mapping_repository.records():
            record = NameNormalizer.normalize(record)

            if record == child_record:
                continue

            parent_keys = set(
                self.key_column_resolver.primary_key_columns_for_record(record)
            )

            if not parent_keys:
                continue

            match_count = len(parent_keys.intersection(child_fk_columns))

            if match_count > best_count:
                best_count = match_count
                best_record = record

        return best_record