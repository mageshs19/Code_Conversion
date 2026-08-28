# LOCATION: src/idms_db2_phase2/generators/sql/sql_line_builder.py
# ACTION: CREATE NEW FILE

"""SQL line builders: SET, WHERE, column list, host list, skipped block."""

from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer


class SqlLineBuilder:
    def __init__(self, host_variable_resolver) -> None:
        self.host_variable_resolver = host_variable_resolver

    def set_lines(
        self,
        table_name: str,
        columns: list[str],
        indent: str,
    ) -> list[str]:
        assignments: list[tuple[str, str]] = []

        for column in columns:
            normalized = NameNormalizer.normalize(column)
            if not normalized:
                continue
            host = self.host_variable_resolver.host_reference_for_column(
                table_name=table_name,
                column_name=normalized,
            )
            if not host:
                continue
            assignments.append((normalized, host))

        output: list[str] = []
        for index, item in enumerate(assignments):
            column, host = item
            suffix = "," if index < len(assignments) - 1 else ""
            output.append(f"{indent}{column} = {host}{suffix}")

        return output

    def where_lines(
        self,
        table_name: str,
        key_columns: list[str],
        indent: str,
    ) -> list[str]:
        """
        Build SQL WHERE lines from composite key columns. The caller passes
        only PK / CALC key columns; FK exclusion is handled upstream.
        """
        conditions: list[tuple[str, str]] = []

        for column in key_columns:
            normalized = NameNormalizer.normalize(column)
            if not normalized:
                continue
            host = self.host_variable_resolver.host_reference_for_column(
                table_name=table_name,
                column_name=normalized,
            )
            if not host:
                continue
            conditions.append((normalized, host))

        output: list[str] = []
        for index, item in enumerate(conditions):
            column, host = item
            prefix = "" if index == 0 else "AND "
            output.append(f"{indent}{prefix}{column} = {host}")

        return output

    def sql_column_list(
        self,
        columns: list[str],
        indent: str,
    ) -> list[str]:
        output: list[str] = []
        for index, column in enumerate(columns):
            suffix = "," if index < len(columns) - 1 else ""
            output.append(f"{indent}{column}{suffix}")
        return output

    def host_variable_list(
        self,
        host_variables: list[str],
        indent: str,
    ) -> list[str]:
        output: list[str] = []
        for index, host in enumerate(host_variables):
            suffix = "," if index < len(host_variables) - 1 else ""
            output.append(f"{indent}{host}{suffix}")
        return output

    def missing_sql(
        self,
        operation: str,
        record_name: str,
        reason: str,
    ) -> list[str]:
        record = NameNormalizer.to_cobol(record_name)
        return [
            f"*DB2: {operation} conversion skipped for {record}.",
            f"*DB2: {reason}.",
            "CONTINUE.",
        ]