# LOCATION: src/idms_db2_phase2/parsers/dclgen/dclgen_column_merger.py
# ACTION: CREATE NEW FILE

"""Merges parsed SQL columns with COBOL host fields into DclgenColumn objects."""

from __future__ import annotations

from catalogs.dclgen_schema import DCLGEN_HOST_FIELD_SUFFIXES_TO_IGNORE
from idms_db2_phase2.domain.models import DclgenColumn
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class DclgenColumnMerger:
    def __init__(self, name_normalizer) -> None:
        self.names = name_normalizer

    def merge_sql_columns_with_cobol_hosts(
        self,
        sql_columns: list[dict[str, object]],
        cobol_fields: list[dict[str, str]],
        fallback_table_name: str,
    ) -> list[DclgenColumn]:
        output: list[DclgenColumn] = []
        usable_hosts = self._usable_host_fields(cobol_fields)

        for index, sql_column in enumerate(sql_columns):
            table_name = self.names.normalize_sql_name(
                str(
                    sql_column.get("table_name", "")
                    or fallback_table_name
                    or ""
                )
            )
            column_name = self.names.normalize_sql_name(
                str(sql_column.get("column_name", ""))
            )
            db2_type = str(sql_column.get("db2_type", "") or "").strip()
            nullable = bool(sql_column.get("nullable", True))

            host = self._best_host_for_column(
                column_name=column_name,
                index=index,
                usable_hosts=usable_hosts,
            )

            output.append(
                DclgenColumn(
                    table_name=table_name,
                    column_name=column_name,
                    db2_type=db2_type,
                    cobol_host_name=host.get("name", column_name),
                    cobol_picture=host.get("picture", ""),
                    cobol_usage=host.get("usage", ""),
                    nullable=nullable,
                )
            )

        return output

    def fallback_columns_from_cobol_fields(
        self,
        table_name: str,
        cobol_fields: list[dict[str, str]],
    ) -> list[DclgenColumn]:
        output: list[DclgenColumn] = []

        for field in self._usable_host_fields(cobol_fields):
            host_name = field.get("name", "")
            if not host_name:
                continue

            output.append(
                DclgenColumn(
                    table_name=table_name,
                    column_name=self.names.normalize_cobol_name_to_db2(
                        host_name
                    ),
                    db2_type="",
                    cobol_host_name=host_name,
                    cobol_picture=field.get("picture", ""),
                    cobol_usage=field.get("usage", ""),
                    nullable=True,
                )
            )

        return output

    def _usable_host_fields(
        self,
        cobol_fields: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        output: list[dict[str, str]] = []
        for field in cobol_fields:
            name = str(field.get("name", "")).upper()
            if not name:
                continue
            if any(
                name.endswith(suffix)
                for suffix in DCLGEN_HOST_FIELD_SUFFIXES_TO_IGNORE
            ):
                continue
            output.append(field)
        return output

    def _best_host_for_column(
        self,
        column_name: str,
        index: int,
        usable_hosts: list[dict[str, str]],
    ) -> dict[str, str]:
        normalized_column = self.names.normalize_compare_name(column_name)

        for host in usable_hosts:
            host_name = self.names.normalize_compare_name(
                host.get("name", "")
            )
            if host_name == normalized_column:
                return host

        for host in usable_hosts:
            host_name = self.names.normalize_compare_name(
                host.get("name", "")
            )
            if normalized_column and normalized_column in host_name:
                return host
            if host_name and host_name in normalized_column:
                return host

        if index < len(usable_hosts):
            return usable_hosts[index]

        return {
            "name": NameNormalizer.to_cobol(column_name),
            "picture": "",
            "usage": "",
        }