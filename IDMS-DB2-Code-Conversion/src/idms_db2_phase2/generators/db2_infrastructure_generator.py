# LOCATION: src/idms_db2_phase2/generators/db2_infrastructure_generator.py
# ACTION: REPLACE ENTIRE FILE

"""
Generates DB2 infrastructure in DATA DIVISION.

Thin facade delegating to focused helpers. Public API preserved:
- apply(cobol_text, operations) -> (text, messages)
- cursor_specs(operations, cobol_text, field_usage_analysis)
- include_names(cursor_specs)
- infrastructure_block(include_names, cursor_specs)
- last_cursor_specs attribute (used by CursorParagraphGenerator)
"""

from __future__ import annotations

from idms_db2_phase2.analyzers.field_usage_analyzer import FieldUsageAnalyzer
from idms_db2_phase2.domain.models import IdmsOperation
from idms_db2_phase2.generators.db2_infrastructure.block_inserter import (
    BlockInserter,
)
from idms_db2_phase2.generators.db2_infrastructure.cobol_line_utils import (
    CobolLineUtils,
)
from idms_db2_phase2.generators.db2_infrastructure.cursor_spec_builder import (
    CursorSpecBuilder,
)
from idms_db2_phase2.generators.db2_infrastructure.infrastructure_block_builder import (
    InfrastructureBlockBuilder,
)
from catalogs.output_sections import DB2_INFRASTRUCTURE_MARKER
from idms_db2_phase2.resolvers.column_name_resolver import ColumnNameResolver
from idms_db2_phase2.resolvers.cursor_column_resolver import (
    CursorColumnResolver,
)
from idms_db2_phase2.resolvers.cursor_name_resolver import CursorNameResolver
from idms_db2_phase2.resolvers.host_variable_resolver import (
    HostVariableResolver,
)
from idms_db2_phase2.resolvers.relationship_resolver import RelationshipResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver


class Db2InfrastructureGenerator:
    def __init__(
        self,
        table_name_resolver: TableNameResolver,
        column_name_resolver: ColumnNameResolver,
        host_variable_resolver: HostVariableResolver,
        cursor_name_resolver: CursorNameResolver,
    ) -> None:
        self.table_name_resolver = table_name_resolver
        self.column_name_resolver = column_name_resolver
        self.host_variable_resolver = host_variable_resolver
        self.cursor_name_resolver = cursor_name_resolver

        self.mapping_repository = table_name_resolver.mapping_repository

        self.relationship_resolver = RelationshipResolver(
            mapping_repository=self.mapping_repository,
            table_name_resolver=self.table_name_resolver,
            host_variable_resolver=self.host_variable_resolver,
        )
        self.cursor_column_resolver = CursorColumnResolver(
            mapping_repository=self.mapping_repository,
            table_name_resolver=self.table_name_resolver,
            column_name_resolver=self.column_name_resolver,
            relationship_resolver=self.relationship_resolver,
        )

        self.line_utils = CobolLineUtils()
        self._spec_builder = CursorSpecBuilder(self)
        self._block_builder = InfrastructureBlockBuilder(self.line_utils)
        self._inserter = BlockInserter(self.line_utils)

        self.last_cursor_specs: list[dict[str, object]] = []

    def apply(
        self,
        cobol_text: str,
        operations: list[IdmsOperation],
    ) -> tuple[str, list[str]]:
        messages: list[str] = []
        text = str(cobol_text or "")

        if not text:
            self.last_cursor_specs = []
            return text, messages

        field_usage_analysis = FieldUsageAnalyzer(
            mapping_repository=self.mapping_repository,
            table_name_resolver=self.table_name_resolver,
        ).analyze(text)
        messages.extend(field_usage_analysis.diagnostics)

        cursor_specs = self.cursor_specs(
            operations=operations,
            cobol_text=text,
            field_usage_analysis=field_usage_analysis,
        )
        self.last_cursor_specs = cursor_specs

        include_names = self.include_names(cursor_specs)
        if include_names:
            messages.append(
                "DB2 infrastructure: DCLGEN includes selected: "
                + ", ".join(include_names)
            )
        else:
            messages.append(
                "DB2 infrastructure: no operation-specific DCLGEN includes "
                "resolved."
            )

        messages.extend(self._spec_builder.spec_messages(cursor_specs))

        if DB2_INFRASTRUCTURE_MARKER in text:
            messages.append(
                "DB2 infrastructure: existing generated DB2 infrastructure "
                "block detected; not inserted again."
            )
            updated = text
        else:
            block = self.infrastructure_block(
                include_names=include_names,
                cursor_specs=cursor_specs,
            )
            updated = self._inserter.insert_in_data_division(
                text=text,
                block=block,
            )
            messages.append(
                "DB2 infrastructure: generated infrastructure block inserted."
            )

        updated = self._inserter.ensure_dclgen_initialization(
            text=updated,
            include_names=include_names,
        )
        return updated, messages

    def cursor_specs(
        self,
        operations: list[IdmsOperation],
        cobol_text: str = "",
        field_usage_analysis=None,
    ) -> list[dict[str, object]]:
        return self._spec_builder.build(
            operations=operations,
            cobol_text=cobol_text,
            field_usage_analysis=field_usage_analysis,
        )

    def include_names(
        self,
        cursor_specs: list[dict[str, object]],
    ) -> list[str]:
        return self._spec_builder.include_names(cursor_specs)

    def infrastructure_block(
        self,
        include_names: list[str],
        cursor_specs: list[dict[str, object]],
    ) -> str:
        return self._block_builder.build(
            include_names=include_names,
            cursor_specs=cursor_specs,
        )

    def _cursor_paragraph_spec(
        self,
        cursor_order: int,
        table_name: str,
    ) -> dict[str, str]:
        if hasattr(self.cursor_name_resolver, "cursor_spec"):
            return self.cursor_name_resolver.cursor_spec(
                cursor_order=cursor_order,
                table_name=table_name,
            )

        cursor_name = self.cursor_name_resolver.cursor_name_from_table(
            table_name
        )
        base = 710 + ((cursor_order - 1) * 100)
        return {
            "cursor_name": cursor_name,
            "open_paragraph": f"{base}-OPEN-{cursor_name}",
            "fetch_paragraph": f"{base + 10}-FETCH-{cursor_name}",
            "close_paragraph": f"{base + 20}-CLOSE-{cursor_name}",
        }