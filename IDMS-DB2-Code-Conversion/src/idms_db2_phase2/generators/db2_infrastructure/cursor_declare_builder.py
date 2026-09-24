# LOCATION: src/idms_db2_phase2/generators/db2_infrastructure/cursor_declare_builder.py
# ACTION: CREATE NEW FILE



from __future__ import annotations

from idms_db2_phase2.generators.db2_infrastructure.cursor_spec import CursorSpec
from rules.db2_infrastructure_rules import (
    DECLARE_TEMPLATE,
    FROM_TEMPLATE,
    IND_EXEC,
    IND_SELECT_FIRST,
    IND_SELECT_NEXT,
    IND_SQL_BODY,
    IND_WHERE_NEXT,
    MISSING_CURSOR_NAME,
    MISSING_TABLE_TEMPLATE,
    SELECT_ALL,
    SELECT_ITEM_FIRST_TEMPLATE,
    SELECT_ITEM_NEXT_TEMPLATE,
    TOKEN_END_EXEC,
    TOKEN_EXEC_SQL,
    TOKEN_FOR_READ_ONLY,
    TOKEN_ORDER_BY,
    TOKEN_SELECT,
    TOKEN_WHERE,
)
from rules.cursor_declaration_rules import (
    EMIT_QUERYNO,
    QUERYNO_BASE,
    QUERYNO_STEP,
    QUERYNO_TEMPLATE,
)

class CursorDeclareBuilder:
    """Renders one DECLARE CURSOR statement."""

    def __init__(self, line_utils) -> None:
        self.line_utils = line_utils

    # =================================================================
    # Public entry point
    # =================================================================
    def build(self, spec: CursorSpec) -> list[str]:
        """One DECLARE CURSOR statement.

        Clause order is fixed by SQL: SELECT, FROM, WHERE, ORDER BY,
        FOR READ ONLY, QUERYNO. QUERYNO must be the last clause inside
        the statement, immediately before END-EXEC.
        """
        if not spec.cursor_name:
            return [MISSING_CURSOR_NAME]

        if not spec.table_name:
            return [MISSING_TABLE_TEMPLATE.format(cursor=spec.cursor_name)]

        columns = spec.select_columns or [SELECT_ALL]

        lines: list[str] = [
            f"{IND_EXEC}{TOKEN_EXEC_SQL}",
            f"{IND_SQL_BODY}"
            f"{DECLARE_TEMPLATE.format(cursor=spec.cursor_name)}",
            f"{IND_SQL_BODY}{TOKEN_SELECT}",
        ]
        lines.extend(self._select_lines(columns))
        lines.append(
            f"{IND_SQL_BODY}{FROM_TEMPLATE.format(table=spec.table_name)}"
        )
        lines.extend(self._where_lines(spec))
        lines.extend(self._order_by_lines(spec))
        lines.append(f"{IND_SQL_BODY}{TOKEN_FOR_READ_ONLY}")
        lines.extend(self._queryno_lines(spec))
        lines.append(f"{IND_EXEC}{TOKEN_END_EXEC}")

        return lines
    
    # =================================================================
    # Clauses
    # =================================================================
    @staticmethod
    def _select_lines(columns: list[str]) -> list[str]:
        """Comma-leading list, so the column names line up."""
        out: list[str] = []

        for index, column in enumerate(columns):
            if index == 0:
                out.append(
                    IND_SELECT_FIRST
                    + SELECT_ITEM_FIRST_TEMPLATE.format(column=column)
                )
            else:
                out.append(
                    IND_SELECT_NEXT
                    + SELECT_ITEM_NEXT_TEMPLATE.format(column=column)
                )

        return out

    def _where_lines(self, spec: CursorSpec) -> list[str]:
        if not spec.where_conditions:
            return []

        return [
            f"{IND_SQL_BODY}{TOKEN_WHERE}",
            *self.line_utils.and_lines(
                items=spec.where_conditions,
                indent=IND_WHERE_NEXT,
            ),
        ]

    @staticmethod
    def _queryno_lines(spec: CursorSpec) -> list[str]:
        """QUERYNO clause, derived from the cursor's position.

        DB2 EXPLAIN identifies a statement by QUERYNO. Without one, an
        access path cannot be tied back to the cursor that produced it.

        The number is DERIVED, never hardcoded, so repeated runs are
        byte-identical and two cursors in the same program can never
        collide:

            QUERYNO_BASE + cursor_order * QUERYNO_STEP
        """
        if not EMIT_QUERYNO:
            return []

        number = QUERYNO_BASE + (spec.cursor_order * QUERYNO_STEP)

        return [
            f"{IND_SQL_BODY}{QUERYNO_TEMPLATE.format(number=number)}"
        ]

    def _order_by_lines(self, spec: CursorSpec) -> list[str]:
        if not spec.order_by_columns:
            return []

        return [
            f"{IND_SQL_BODY}{TOKEN_ORDER_BY}",
            *self.line_utils.comma_lines(
                items=spec.order_by_columns,
                indent=IND_WHERE_NEXT,
            ),
        ]