# LOCATION: src/idms_db2_phase2/generators/db2_infrastructure/infrastructure_block_builder.py
# ACTION: CREATE NEW FILE

"""Builds the generated DB2 infrastructure DATA DIVISION block."""

from __future__ import annotations

from catalogs.output_sections import (
    DB2_CURSOR_DECLARATIONS_MARKER,
    DB2_CURSOR_FLAGS_MARKER,
    DB2_INFRASTRUCTURE_MARKER,
    DB2_SQL_ERROR_LOCATION_MARKER,
    SQLCA_INCLUDE_NAME,
    SQLERRWS_INCLUDE_NAME,
)
from idms_db2_phase2.services.name_normalizer import NameNormalizer

try:
    from catalogs.output_sections import (
        SQL_LOCATION_FIELD_NAME,
        SQL_LOCATION_PICTURE,
    )
except ImportError:
    SQL_LOCATION_FIELD_NAME = "SQL-LOCATION"
    SQL_LOCATION_PICTURE = "PIC X(40) VALUE SPACES."


class InfrastructureBlockBuilder:
    def __init__(self, line_utils) -> None:
        self.line_utils = line_utils

    def build(
        self,
        include_names: list[str],
        cursor_specs: list[dict[str, object]],
    ) -> str:
        lines: list[str] = []

        lines.extend(self.line_utils.comment_block(DB2_INFRASTRUCTURE_MARKER))
        lines.extend(
            self._include_lines(
                include_names=[
                    SQLERRWS_INCLUDE_NAME,
                    SQLCA_INCLUDE_NAME,
                    *include_names,
                ]
            )
        )
        lines.append("")
        lines.extend(
            self.line_utils.comment_block(DB2_SQL_ERROR_LOCATION_MARKER)
        )
        lines.append(
            f"01  {SQL_LOCATION_FIELD_NAME:<30} {SQL_LOCATION_PICTURE}"
        )

        if cursor_specs:
            lines.append("")
            lines.extend(
                self.line_utils.comment_block(DB2_CURSOR_FLAGS_MARKER)
            )
            lines.extend(self._cursor_flag_lines(cursor_specs))

            lines.append("")
            lines.extend(
                self.line_utils.comment_block(DB2_CURSOR_DECLARATIONS_MARKER)
            )
            for spec in cursor_specs:
                lines.extend(self._cursor_declaration(spec))
                lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def _cursor_flag_lines(
        self,
        cursor_specs: list[dict[str, object]],
    ) -> list[str]:
        lines: list[str] = []

        for spec in cursor_specs:
            cursor_name = NameNormalizer.to_cobol(
                str(spec.get("cursor_name", ""))
            )
            if not cursor_name:
                continue

            flag_name = f"WS-{cursor_name}-FLAG"
            not_eoc_name = f"{cursor_name}-NOT-EOC"
            eoc_name = f"{cursor_name}-EOC"

            lines.append(f"01  {flag_name:<30} PIC X.")
            lines.append(f"    88  {not_eoc_name:<26} VALUE 'N'.")
            lines.append(f"    88  {eoc_name:<26} VALUE 'Y'.")
            lines.append("")

        return lines

    def _cursor_declaration(
        self,
        spec: dict[str, object],
    ) -> list[str]:
        cursor_name = NameNormalizer.to_cobol(
            str(spec.get("cursor_name", ""))
        )
        table_name = NameNormalizer.normalize(str(spec.get("table_name", "")))

        select_columns = [
            NameNormalizer.normalize(str(column))
            for column in list(spec.get("select_columns", []))
            if NameNormalizer.normalize(str(column))
        ]
        where_conditions = [
            str(condition or "").strip()
            for condition in list(spec.get("where_conditions", []))
            if str(condition or "").strip()
        ]
        order_by_columns = [
            str(column or "").strip()
            for column in list(spec.get("order_by_columns", []))
            if str(column or "").strip()
        ]

        if not cursor_name:
            return [
                "* DB2 WARNING: Unable to declare cursor; missing cursor "
                "name."
            ]
        if not table_name:
            return [
                f"* DB2 WARNING: Unable to declare cursor {cursor_name}; "
                f"missing DB2 table mapping."
            ]

        if not select_columns:
            select_columns = ["*"]

        lines: list[str] = [
            "EXEC SQL",
            f"    DECLARE {cursor_name} CURSOR WITH HOLD FOR",
            "    SELECT",
        ]
        lines.extend(self._select_lines(columns=select_columns))
        lines.append(f"    FROM {table_name}")

        if where_conditions:
            lines.append("    WHERE")
            lines.extend(
                self.line_utils.and_lines(
                    items=where_conditions,
                    indent="       ",
                )
            )

        if order_by_columns:
            lines.append("    ORDER BY")
            lines.extend(
                self.line_utils.comma_lines(
                    items=order_by_columns,
                    indent="       ",
                )
            )

        lines.append("    FOR READ ONLY")
        lines.append("END-EXEC.")
        return lines

    def _select_lines(self, columns: list[str]) -> list[str]:
        clean_columns = [
            NameNormalizer.normalize(column)
            for column in columns
            if NameNormalizer.normalize(column)
        ]
        output: list[str] = []
        for index, column in enumerate(clean_columns):
            if index == 0:
                output.append(f"        {column}")
            else:
                output.append(f"       , {column}")
        return output

    def _include_lines(self, include_names: list[str]) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for include_name in include_names:
            normalized = self.line_utils.normalize_include_name(include_name)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            output.extend(
                [
                    "EXEC SQL",
                    f"    INCLUDE {normalized}",
                    "END-EXEC.",
                ]
            )

        return output