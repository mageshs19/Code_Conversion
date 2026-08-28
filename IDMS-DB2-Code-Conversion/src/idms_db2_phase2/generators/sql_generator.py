# LOCATION: src/idms_db2_phase2/generators/sql_generator.py
# ACTION: REPLACE ENTIRE FILE

"""
Generates DB2 embedded SQL snippets.

Authority:
- Sheet Mapping determines intended DB2 table and column names.
- DCLGEN determines final table availability, host variable spelling.
- TableNameResolver resolves TB/TV mismatches using DCLGEN.

Thin facade delegating to focused SQL builders. Public API preserved:
select_by_key, insert, update, delete, commit, rollback,
changed_field_move, missing_mapping, and the .messages attribute.
"""

from __future__ import annotations

from idms_db2_phase2.generators.sql.sql_column_resolver import (
    SqlColumnResolver,
)
from idms_db2_phase2.generators.sql.sql_date_move_builder import (
    SqlDateMoveBuilder,
)
from idms_db2_phase2.generators.sql.sql_line_builder import SqlLineBuilder
from idms_db2_phase2.generators.sql.sql_statement_builder import (
    SqlStatementBuilder,
)
from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.column_name_resolver import ColumnNameResolver
from idms_db2_phase2.resolvers.host_variable_resolver import (
    HostVariableResolver,
)
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.resolvers.update_sql_plan_resolver import (
    UpdateSqlPlanResolver,
)


class SqlGenerator:
    def __init__(
        self,
        mapping_repository: MappingRepository,
        dclgen_repository: DclgenRepository,
        table_name_resolver: TableNameResolver,
        column_name_resolver: ColumnNameResolver,
        host_variable_resolver: HostVariableResolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.dclgen_repository = dclgen_repository
        self.table_name_resolver = table_name_resolver
        self.column_name_resolver = column_name_resolver
        self.host_variable_resolver = host_variable_resolver
        self.messages: list[str] = []

        self.update_plan_resolver = UpdateSqlPlanResolver(
            mapping_repository=mapping_repository,
            dclgen_repository=dclgen_repository,
            table_name_resolver=table_name_resolver,
            host_variable_resolver=host_variable_resolver,
        )

        column_resolver = SqlColumnResolver(
            mapping_repository=mapping_repository,
            dclgen_repository=dclgen_repository,
            table_name_resolver=table_name_resolver,
        )
        line_builder = SqlLineBuilder(
            host_variable_resolver=host_variable_resolver,
        )
        date_builder = SqlDateMoveBuilder()

        self._statements = SqlStatementBuilder(
            column_resolver=column_resolver,
            line_builder=line_builder,
            date_builder=date_builder,
            host_variable_resolver=host_variable_resolver,
            mapping_repository=mapping_repository,
            update_plan_resolver=self.update_plan_resolver,
        )

    def select_by_key(self, record_name: str) -> list[str]:
        lines = self._statements.select_by_key(record_name)
        self.messages = self._statements.messages
        return lines

    def insert(self, record_name: str) -> list[str]:
        lines = self._statements.insert(record_name)
        self.messages = self._statements.messages
        return lines

    def update(
        self,
        record_name: str,
        changed_source_fields: list[str] | None = None,
    ) -> list[str]:
        lines = self._statements.update(
            record_name=record_name,
            changed_source_fields=changed_source_fields,
        )
        self.messages = self._statements.messages
        return lines

    def delete(self, record_name: str) -> list[str]:
        lines = self._statements.delete(record_name)
        self.messages = self._statements.messages
        return lines

    def commit(self) -> list[str]:
        return self._statements.commit()

    def rollback(self) -> list[str]:
        return self._statements.rollback()

    def changed_field_move(
        self,
        record_name: str,
        source_value: str,
        target_source_field: str,
    ) -> list[str]:
        return self._statements.changed_field_move(
            record_name=record_name,
            source_value=source_value,
            target_source_field=target_source_field,
        )

    def missing_mapping(
        self,
        record_name: str,
        reason: str,
    ) -> list[str]:
        return self._statements.missing_mapping(
            record_name=record_name,
            reason=reason,
        )