# LOCATION: src/idms_db2_phase2/generators/sql/sql_statement_builder.py
# ACTION: REPLACE ENTIRE FILE

"""Builds DB2 statement bodies: INSERT / UPDATE / DELETE / SELECT-skip / MOVE."""

from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.update_sql_cleanup_rules import UPDATE_QUERYNO


class SqlStatementBuilder:
    def __init__(
        self,
        column_resolver,
        line_builder,
        date_builder,
        host_variable_resolver,
        mapping_repository,
        update_plan_resolver,
    ) -> None:
        self.column_resolver = column_resolver
        self.line_builder = line_builder
        self.date_builder = date_builder
        self.host_variable_resolver = host_variable_resolver
        self.mapping_repository = mapping_repository
        self.update_plan_resolver = update_plan_resolver
        self.messages: list[str] = []

    def _sqlcode_evaluate_block(self, operation: str, table: str) -> list[str]:
        """Manual-standard SQLCODE handling shared by INSERT/UPDATE/DELETE."""
        return [
            f"   QUERYNO {UPDATE_QUERYNO}",
            "END-EXEC",
            "EVALUATE SQLCODE",
            "    WHEN 0",
            "         CONTINUE",
            "    WHEN OTHER",
            f"         DISPLAY 'ERROR ON {operation} {table}'",
            "         PERFORM SQLERROR",
            "END-EVALUATE",
            ".",
        ]

    def select_by_key(self, record_name: str) -> list[str]:
        self.messages = []
        record = NameNormalizer.normalize(record_name)
        table = self.column_resolver.resolved_table_for_record(record)

        if not record or not table:
            return self.line_builder.missing_sql(
                operation="OBTAIN CALC",
                record_name=record_name,
                reason="missing Sheet Mapping or DCLGEN table metadata",
            )

        key_columns = self.column_resolver.key_columns_for_record(
            record_name=record,
            table_name=table,
        )
        if not key_columns:
            return self.line_builder.missing_sql(
                operation="OBTAIN CALC",
                record_name=record,
                reason="missing key column metadata",
            )

        return [
            f"*DB2: Removed OBTAIN CALC SELECT for "
            f"{NameNormalizer.to_cobol(record)}.",
            "*DB2: Direct UPDATE will use mapped composite key WHERE clause.",
            "CONTINUE.",
        ]

    def insert(self, record_name: str) -> list[str]:
        self.messages = []
        record = NameNormalizer.normalize(record_name)
        table = self.column_resolver.resolved_table_for_record(record)

        if not record or not table:
            return self.line_builder.missing_sql(
                operation="INSERT",
                record_name=record_name,
                reason="missing Sheet Mapping or DCLGEN table metadata",
            )

        columns = self.column_resolver.insert_columns_for_record(
            record_name=record,
            table_name=table,
        )
        if not columns:
            return self.line_builder.missing_sql(
                operation="INSERT",
                record_name=record,
                reason="missing insert columns",
            )

        host_variables = (
            self.host_variable_resolver.host_references_for_columns(
                table_name=table,
                columns=columns,
            )
        )
        if not host_variables:
            return self.line_builder.missing_sql(
                operation="INSERT",
                record_name=record,
                reason="missing INSERT host variables in DCLGEN",
            )

        lines: list[str] = [
            f"*DB2: Converted STORE for {NameNormalizer.to_cobol(record)}.",
            f"MOVE 'INSERT-{NameNormalizer.to_cobol(record)}' "
            f"TO SQL-LOCATION.",
            "EXEC SQL",
            f"   INSERT INTO {table}",
            "      (",
        ]
        lines.extend(
            self.line_builder.sql_column_list(columns, indent="       ")
        )
        lines.extend(["      )", "   VALUES", "      ("])
        lines.extend(
            self.line_builder.host_variable_list(
                host_variables, indent="       "
            )
        )
        lines.append("      )")
        lines.extend(self._sqlcode_evaluate_block("INSERT", table))
        return lines

    def update(
        self,
        record_name: str,
        changed_source_fields: list[str] | None = None,
    ) -> list[str]:
        self.messages = []
        record = NameNormalizer.normalize(record_name)
        plan = self.update_plan_resolver.resolve(
            record_name=record,
            changed_source_fields=changed_source_fields or [],
        )
        self.messages.extend(plan.diagnostics)

        if plan.table_name:
            plan.key_columns = self.column_resolver.key_columns_for_record(
                record_name=record,
                table_name=plan.table_name,
            )

        if not plan.is_complete:
            return self.line_builder.missing_sql(
                operation="UPDATE",
                record_name=record,
                reason="incomplete conservative UPDATE metadata",
            )

        set_lines = self.line_builder.set_lines(
            table_name=plan.table_name,
            columns=plan.update_columns,
            indent="      ",
        )
        where_lines = self.line_builder.where_lines(
            table_name=plan.table_name,
            key_columns=plan.key_columns,
            indent="      ",
        )
        if not set_lines or not where_lines:
            return self.line_builder.missing_sql(
                operation="UPDATE",
                record_name=record,
                reason="missing SET or WHERE host variables in DCLGEN",
            )

        lines: list[str] = [
            f"*DB2: Converted MODIFY for {NameNormalizer.to_cobol(record)}.",
            f"MOVE 'UPDATE-{NameNormalizer.to_cobol(record)}' "
            f"TO SQL-LOCATION.",
            "EXEC SQL",
            f"   UPDATE {plan.table_name}",
            "   SET",
        ]
        lines.extend(set_lines)
        lines.append("   WHERE")
        lines.extend(where_lines)
        lines.extend(self._sqlcode_evaluate_block("UPDATE", plan.table_name))
        return lines

    def delete(self, record_name: str) -> list[str]:
        self.messages = []
        record = NameNormalizer.normalize(record_name)
        table = self.column_resolver.resolved_table_for_record(record)

        if not record or not table:
            return self.line_builder.missing_sql(
                operation="DELETE",
                record_name=record_name,
                reason="missing Sheet Mapping or DCLGEN table metadata",
            )

        key_columns = self.column_resolver.key_columns_for_record(
            record_name=record,
            table_name=table,
        )
        where_lines = self.line_builder.where_lines(
            table_name=table,
            key_columns=key_columns,
            indent="      ",
        )
        if not where_lines:
            return self.line_builder.missing_sql(
                operation="DELETE",
                record_name=record,
                reason="missing DELETE key host variables in DCLGEN",
            )

        lines: list[str] = [
            f"*DB2: Converted ERASE for {NameNormalizer.to_cobol(record)}.",
            f"MOVE 'DELETE-{NameNormalizer.to_cobol(record)}' "
            f"TO SQL-LOCATION.",
            "EXEC SQL",
            f"   DELETE FROM {table}",
            "   WHERE",
        ]
        lines.extend(where_lines)
        lines.extend(self._sqlcode_evaluate_block("DELETE", table))
        return lines

    def commit(self) -> list[str]:
        return [
            "MOVE 'COMMIT' TO SQL-LOCATION.",
            "EXEC SQL",
            "   COMMIT",
            "END-EXEC.",
        ]

    def rollback(self) -> list[str]:
        return [
            "MOVE 'ROLLBACK' TO SQL-LOCATION.",
            "EXEC SQL",
            "   ROLLBACK",
            "END-EXEC.",
        ]

    def changed_field_move(
        self,
        record_name: str,
        source_value: str,
        target_source_field: str,
    ) -> list[str]:
        record = NameNormalizer.normalize(record_name)
        table = self.column_resolver.resolved_table_for_record(record)
        column = self.mapping_repository.column_for_source_field(
            record_name=record,
            source_field_name=target_source_field,
        )
        column = NameNormalizer.normalize(column)

        if not table or not column:
            return [
                f"*DB2: Conversion skipped for MOVE target "
                f"{target_source_field}.",
                "*DB2: Missing Sheet Mapping or DCLGEN metadata.",
                "CONTINUE.",
            ]

        host_key = self.host_variable_resolver.host_reference_key(
            table_name=table,
            column_name=column,
        )
        if not host_key:
            return [
                f"*DB2: Conversion skipped for MOVE target "
                f"{target_source_field}.",
                "*DB2: Missing DCLGEN host variable.",
                "CONTINUE.",
            ]

        if self.date_builder.is_db2_date_column(column):
            return self.date_builder.date_ymd8_to_db2_external_move(
                source_value=source_value,
                host_key=host_key,
            )

        return [f"MOVE {source_value} TO {host_key}"]

    def missing_mapping(
        self,
        record_name: str,
        reason: str,
    ) -> list[str]:
        return self.line_builder.missing_sql(
            operation="DB2",
            record_name=record_name,
            reason=reason,
        )