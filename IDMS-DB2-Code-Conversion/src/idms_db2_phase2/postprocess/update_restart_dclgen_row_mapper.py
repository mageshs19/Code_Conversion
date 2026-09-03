from __future__ import annotations

from typing import Any

from catalogs.dclgen_schema import DCLGEN_GROUP_PREFIX
from idms_db2_phase2.postprocess.update_metadata_models import (
    include_from_label,
    upper,
    value,
)


class UpdateRestartDclgenRowMapper:
    """
    Converts parsed DCLGEN column objects into normalized row dictionaries.

    This class does not decide restart roles.
    It only normalizes metadata from parser output into consistent keys used
    by the restart resolver.

    The DCLGEN parser commonly exposes:
    - table_name
    - column_name
    - cobol_host_name
    - cobol_picture
    - cobol_usage

    This mapper must therefore read cobol_host_name as the COBOL host field.
    """

    def column_row(
        self,
        item: Any,
    ) -> dict[str, str]:
        table_name = upper(
            value(
                item,
                "table_name",
                "db2_table_name",
                "table",
                default="",
            )
        )

        source_label = value(
            item,
            "source_label",
            "file_name",
            "filename",
            default="",
        )

        include_name = upper(
            value(
                item,
                "include_name",
                "dclgen_name",
                "dclgen_include",
                default="",
            )
        )

        if not include_name:
            include_name = upper(include_from_label(source_label))

        column_name = upper(
            value(
                item,
                "column_name",
                "db2_column_name",
                "column",
                "name",
                default="",
            )
        )

        cobol_host_name = upper(
            value(
                item,
                "cobol_host_name",
                "host_variable",
                "host_name",
                "host_field",
                "field",
                "cobol_name",
                default="",
            )
        )

        host_record = upper(
            value(
                item,
                "host_record_name",
                "host_record",
                "host_group",
                "cobol_host_group",
                "cobol_group_name",
                "dclgen_record_name",
                "dclgen_record",
                "record_name",
                default="",
            )
        )

        if not host_record and table_name:
            host_record = f"{DCLGEN_GROUP_PREFIX}{table_name}"

        cobol_picture = upper(
            value(
                item,
                "cobol_picture",
                "picture",
                "pic",
                default="",
            )
        )

        cobol_usage = upper(
            value(
                item,
                "cobol_usage",
                "usage",
                default="",
            )
        )

        return {
            "table_name": table_name,
            "include_name": include_name,
            "host_record": host_record,
            "column": column_name,
            "field": cobol_host_name,
            "picture": cobol_picture,
            "usage": cobol_usage,
            "source_label": upper(source_label),
        }

    def first_value(
        self,
        rows: list[dict[str, str]],
        key: str,
    ) -> str:
        for row in rows:
            text = str(row.get(key, "") or "").strip()
            if text:
                return text

        return ""