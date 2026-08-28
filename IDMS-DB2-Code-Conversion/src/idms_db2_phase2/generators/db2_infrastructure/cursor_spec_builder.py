# LOCATION: src/idms_db2_phase2/generators/db2_infrastructure/cursor_spec_builder.py
# ACTION: CREATE NEW FILE

"""Builds cursor specifications from IDMS operations."""

from __future__ import annotations

from idms_db2_phase2.analyzers.field_usage_analyzer import FieldUsageAnalyzer
from idms_db2_phase2.domain.models import IdmsOperation
from idms_db2_phase2.services.name_normalizer import NameNormalizer

CURSOR_OPERATIONS = {
    "OBTAIN_FIRST",
    "OBTAIN_NEXT",
    "FIND_FIRST",
}


class CursorSpecBuilder:
    def __init__(self, owner) -> None:
        # owner exposes resolvers, mapping_repository, cursor_column_resolver,
        # relationship_resolver, cursor_name_resolver, table_name_resolver,
        # host_variable_resolver, _cursor_paragraph_spec.
        self.owner = owner

    def build(
        self,
        operations: list[IdmsOperation],
        cobol_text: str = "",
        field_usage_analysis=None,
    ) -> list[dict[str, object]]:
        output: list[dict[str, object]] = []
        seen: set[tuple[str, str, str]] = set()
        cursor_order = 1

        if field_usage_analysis is None:
            field_usage_analysis = FieldUsageAnalyzer(
                mapping_repository=self.owner.mapping_repository,
                table_name_resolver=self.owner.table_name_resolver,
            ).analyze(cobol_text)

        for operation in operations or []:
            operation_name = str(operation.operation or "").upper()
            if operation_name not in CURSOR_OPERATIONS:
                continue

            record_name = NameNormalizer.normalize(operation.record_name)
            set_name = NameNormalizer.normalize(operation.set_name)
            if not record_name:
                continue

            table_name = self.owner.table_name_resolver.table_for_record(
                record_name
            )
            if not table_name:
                continue

            key = (set_name, record_name, table_name)
            if key in seen:
                continue
            seen.add(key)

            cursor_name = (
                self.owner.cursor_name_resolver.cursor_name_from_table(
                    table_name
                )
            )
            paragraph_spec = self.owner._cursor_paragraph_spec(
                cursor_order=cursor_order,
                table_name=table_name,
            )
            select_columns = (
                self.owner.cursor_column_resolver.select_columns_for_record(
                    record_name=record_name,
                    field_usage_analysis=field_usage_analysis,
                )
            )
            relationship = (
                self.owner.relationship_resolver.resolve_for_child_record(
                    record_name
                )
            )
            where_conditions = self._where_conditions_from_relationship(
                relationship.conditions
            )
            order_by_columns = (
                self.owner.cursor_column_resolver.order_by_columns_for_record(
                    record_name
                )
            )
            host_variables = (
                self.owner.host_variable_resolver.host_references_for_columns(
                    table_name=table_name,
                    columns=select_columns,
                )
            )

            output.append(
                {
                    "set_name": set_name,
                    "record_name": record_name,
                    "table_name": table_name,
                    "cursor_name": cursor_name,
                    "select_columns": select_columns,
                    "host_variables": host_variables,
                    "where_conditions": where_conditions,
                    "order_by_columns": order_by_columns,
                    "open_paragraph": paragraph_spec["open_paragraph"],
                    "fetch_paragraph": paragraph_spec["fetch_paragraph"],
                    "close_paragraph": paragraph_spec["close_paragraph"],
                    "cursor_order": cursor_order,
                }
            )
            cursor_order += 1

        return output

    def include_names(
        self,
        cursor_specs: list[dict[str, object]],
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for spec in cursor_specs or []:
            table_name = NameNormalizer.normalize(
                str(spec.get("table_name", ""))
            )
            if not table_name:
                continue
            include_name = self.owner.line_utils.normalize_include_name(
                table_name
            )
            if not include_name or include_name in seen:
                continue
            seen.add(include_name)
            output.append(include_name)

        return output

    def spec_messages(
        self,
        cursor_specs: list[dict[str, object]],
    ) -> list[str]:
        messages: list[str] = []

        for spec in cursor_specs:
            cursor_name = str(spec.get("cursor_name", ""))
            record_name = str(spec.get("record_name", ""))
            table_name = str(spec.get("table_name", ""))
            select_columns = list(spec.get("select_columns", []))
            host_variables = list(spec.get("host_variables", []))

            if not table_name:
                messages.append(
                    f"DB2 infrastructure: cursor {cursor_name} has no "
                    f"resolved DB2 table for record {record_name}."
                )
            if not select_columns:
                messages.append(
                    f"DB2 infrastructure: cursor {cursor_name} has no "
                    f"resolved SELECT columns for record {record_name}."
                )
            if not host_variables:
                messages.append(
                    f"DB2 infrastructure: cursor {cursor_name} has no "
                    f"resolved FETCH host variables for record {record_name}."
                )

        return messages

    def _where_conditions_from_relationship(self, conditions) -> list[str]:
        output: list[str] = []
        for condition in conditions or []:
            child_column = NameNormalizer.normalize(
                getattr(condition, "child_column", "")
            )
            parent_host = str(
                getattr(condition, "parent_host_reference", "") or ""
            ).strip()
            if not child_column or not parent_host:
                continue
            output.append(f"{child_column} = {parent_host}")
        return output