# LOCATION: src/idms_db2_phase2/composers/update_sql_cleanup/sql_line_mixin.py
# ACTION: CREATE NEW FILE

"""Host-reference and SET/WHERE/comma line-builder mixin."""

from __future__ import annotations


class SqlLineMixin:
    def _host_reference(
        self,
        table: str,
        column: str,
    ) -> str:
        return self.host_variable_resolver.host_reference_for_column(
            table_name=table,
            column_name=column,
        )

    def _host_reference_key(
        self,
        table: str,
        column: str,
    ) -> str:
        if hasattr(self.host_variable_resolver, "host_reference_key"):
            return self.host_variable_resolver.host_reference_key(
                table_name=table,
                column_name=column,
            )

        reference = self._host_reference(table, column)

        if reference.startswith(":"):
            return reference[1:].strip()

        return reference

    def _set_lines(
        self,
        table: str,
        columns: list[str],
        indent: str,
    ) -> list[str]:
        output: list[str] = []

        for index, column in enumerate(columns):
            host = self._host_reference(table, column)
            if not host:
                continue
            suffix = "," if index < len(columns) - 1 else ""
            output.append(f"{indent}{column} = {host}{suffix}")

        return output

    def _where_lines(
        self,
        table: str,
        columns: list[str],
        indent: str,
    ) -> list[str]:
        output: list[str] = []

        for index, column in enumerate(columns):
            host = self._host_reference(table, column)
            if not host:
                continue
            prefix = "" if index == 0 else "AND "
            output.append(f"{indent}{prefix}{column} = {host}")

        return output

    def _comma_lines(
        self,
        values: list[str],
        indent: str,
    ) -> list[str]:
        output: list[str] = []

        for index, value in enumerate(values):
            suffix = "," if index < len(values) - 1 else ""
            output.append(f"{indent}{value}{suffix}")

        return output