# LOCATION: src/idms_db2_phase2/generators/db2_infrastructure/infrastructure_block_builder.py
# ACTION: REPLACE ENTIRE FILE

"""Builds the generated DB2 infrastructure DATA DIVISION block.

Emits, in order:
  1. Infrastructure marker comment
  2. SQLERRWS / SQLCA / DCLGEN INCLUDE statements
  3. SQL-LOCATION declaration  (SUPPRESSED - see _sql_location_lines)
  4. Cursor end-of-cursor flag group
  5. Cursor DECLARE statements

Layout literals live in catalogs/output_sections.py. No program, record,
table, cursor or host variable name is hardcoded here.
"""

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
        DECLARE_SQL_LOCATION_FIELD,
        SQL_LOCATION_FIELD_NAME,
        SQL_LOCATION_PICTURE,
    )
except ImportError:
    DECLARE_SQL_LOCATION_FIELD = False
    SQL_LOCATION_FIELD_NAME = "SQL-LOCATION"
    SQL_LOCATION_PICTURE = "PIC X(40) VALUE SPACES."


class InfrastructureBlockBuilder:
    """Renders the DB2 infrastructure block for WORKING-STORAGE."""

    def __init__(self, line_utils) -> None:
        self.line_utils = line_utils

    # =================================================================
    # Public entry point
    # =================================================================
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

        lines.extend(self._sql_location_lines())

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

    # =================================================================
    # SQL-LOCATION
    # =================================================================
    def _sql_location_lines(self) -> list[str]:
        """SQL-LOCATION declaration block.

        SQLERRWS already declares SQL-LOCATION. Declaring it again
        produces a duplicate data-name, and the COBOL team's manual
        reference program carries no local declaration at all.

        Controlled by catalogs/output_sections.DECLARE_SQL_LOCATION_FIELD.
        """
        if not DECLARE_SQL_LOCATION_FIELD:
            return []

        return [
            "",
            *self.line_utils.comment_block(DB2_SQL_ERROR_LOCATION_MARKER),
            f"01  {SQL_LOCATION_FIELD_NAME:<30} {SQL_LOCATION_PICTURE}",
        ]

    # =================================================================
    # Cursor end-of-cursor flags
    # =================================================================
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

    # =================================================================
    # Cursor declarations
    # =================================================================
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
            for column in list(spec.get("select_columns", []) or [])
            if NameNormalizer.normalize(str(column))
        ]
        where_conditions = [
            str(condition or "").strip()
            for condition in list(spec.get("where_conditions", []) or [])
            if str(condition or "").strip()
        ]
        order_by_columns = [
            str(column or "").strip()
            for column in list(spec.get("order_by_columns", []) or [])
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
            f"   DECLARE {cursor_name} CURSOR WITH HOLD FOR",
            "   SELECT",
        ]
        lines.extend(self._select_lines(columns=select_columns))
        lines.append(f"   FROM {table_name}")

        if where_conditions:
            lines.append("   WHERE")
            lines.extend(
                self.line_utils.and_lines(
                    items=where_conditions,
                    indent="      ",
                )
            )

        if order_by_columns:
            lines.append("   ORDER BY")
            lines.extend(
                self.line_utils.comma_lines(
                    items=order_by_columns,
                    indent="      ",
                )
            )

        lines.append("   FOR READ ONLY")
        lines.append("END-EXEC.")
        return lines

    # =================================================================
    # Line helpers
    # =================================================================
    @staticmethod
    def _select_lines(columns: list[str]) -> list[str]:
        clean_columns = [
            NameNormalizer.normalize(column)
            for column in columns
            if NameNormalizer.normalize(column)
        ]

        output: list[str] = []
        for index, column in enumerate(clean_columns):
            if index == 0:
                output.append(f"       {column}")
            else:
                output.append(f"      , {column}")

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
                    f"   INCLUDE {normalized}",
                    "END-EXEC.",
                ]
            )

        return output