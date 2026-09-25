# LOCATION: src/idms_db2_phase2/generators/db2_infrastructure/cursor_declare_builder.py
# ACTION: REPLACE ENTIRE FILE
"""Renders one DECLARE CURSOR statement.

Clause order is fixed by SQL and by the manual reference:

    SELECT, FROM, WHERE, ORDER BY, FOR READ ONLY, QUERYNO

QUERYNO is the LAST clause inside the statement, immediately before
END-EXEC, so DB2 EXPLAIN can tie an access path back to the cursor.

CORRECTION 1 - 'SELECT *' was emitted when the column list was empty.
               ENFORCE_CURSOR_EXPLICIT_COLUMNS forbids it and CHK-12.04
               rejects it. The builder now refuses with a warning.
CORRECTION 2 - the WHERE column-ownership guard was lost. A parent
               column on the left of a child predicate is SQLCODE -206
               at bind time.
CORRECTION 3 - a WHERE-less cursor was emitted silently. Every
               declaration decision is now reported on self.messages.
CORRECTION 4 - a RESOLVED ORDER BY was deleted.

               This builder used to drop ORDER BY from any cursor with
               no WHERE, on the premise that "the manual reference never
               orders a parent cursor". That premise came from ONE
               sample - the BEFF / EVEF reference family - and is false
               in general. Manual reference VMDZ7200 (Train Case 3) ends
               its ROOT cursor with

                   ORDER BY NR_ID_479BFAS ASC
                   FOR READ ONLY
                   QUERYNO 254

               Row sequence is business meaning: an IDMS set walk has an
               order and the output extract inherits it, so deleting the
               clause silently reorders the file for every downstream
               consumer.

               GOVERNING RULE: the converter may REFUSE to generate a
               clause it cannot resolve. It must never DELETE one that
               has been resolved.

               PARENT_CURSOR_KEEPS_ORDER_BY and
               CHILD_CURSOR_KEEPS_ORDER_BY are retained so the previous
               behaviour can be reproduced deliberately for a diff, but
               ENFORCE_ORDER_BY_RETENTION guards them and both now
               default to True.
"""

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
    CHILD_CURSOR_KEEPS_ORDER_BY,
    DECLARATION_MESSAGES,
    EMIT_QUERYNO,
    ENFORCE_ORDER_BY_RETENTION,
    ENFORCE_WHERE_COLUMN_OWNERSHIP,
    MISSING_COLUMNS_TEMPLATE,
    PARENT_CURSOR_KEEPS_ORDER_BY,
    QUERYNO_BASE,
    QUERYNO_STEP,
    QUERYNO_TEMPLATE,
    SWEEP_CURSOR_NO_WHERE_TEMPLATE,
    UNRESOLVED_JOIN_KEY_TEMPLATE,
    ENFORCE_ORDER_BY_COLUMN_OWNERSHIP,
    NON_COLUMN_SENTINELS,
    ORDER_BY_DIRECTIONS,
)

OPERATOR_TOKENS = ("=", "<>", "<", ">", "!")


class CursorDeclareBuilder:
    """Renders one DECLARE CURSOR statement."""

    def __init__(
        self,
        line_utils,
        column_name_resolver=None,
    ) -> None:
        self.line_utils = line_utils
        # Optional. When absent, ownership cannot be validated and the
        # guard stands down rather than refusing a valid cursor.
        self.column_name_resolver = column_name_resolver
        self.messages: list[str] = []

    # =================================================================
    # Public entry point
    # =================================================================
    def build(self, spec: CursorSpec) -> list[str]:
        if not spec.cursor_name:
            return [MISSING_CURSOR_NAME]

        if not spec.table_name:
            return [MISSING_TABLE_TEMPLATE.format(cursor=spec.cursor_name)]

        columns = list(spec.select_columns or [])
        if not columns:
            # Refusing beats SELECT *: CHK-12.04 forbids selecting
            # every column, and an implicit list breaks FETCH parity.
            self._log(
                DECLARATION_MESSAGES["select_all_refused"].format(
                    cursor=spec.cursor_name
                )
            )
            return [
                MISSING_COLUMNS_TEMPLATE.format(
                    cursor=spec.cursor_name,
                    table=spec.table_name,
                )
            ]

        conditions = self._conditions(spec)

        unowned = self._unowned_condition(conditions, spec.table_name)
        if ENFORCE_WHERE_COLUMN_OWNERSHIP and unowned:
            self._log(
                DECLARATION_MESSAGES["join_key_unresolved"].format(
                    column=unowned,
                    table=spec.table_name,
                    cursor=spec.cursor_name,
                )
            )
            return [
                UNRESOLVED_JOIN_KEY_TEMPLATE.format(
                    cursor=spec.cursor_name,
                    column=unowned,
                    table=spec.table_name,
                )
            ]

        has_where = bool(conditions)
        if has_where:
            self._log(
                DECLARATION_MESSAGES["where_declared"].format(
                    cursor=spec.cursor_name,
                    count=len(conditions),
                )
            )
        else:
            self._log(
                SWEEP_CURSOR_NO_WHERE_TEMPLATE.format(
                    cursor=spec.cursor_name,
                    table=spec.table_name,
                )
            )

        order_by = self._order_by_columns(spec, has_where)

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
        lines.extend(self._where_lines(conditions))
        lines.extend(self._order_by_lines(order_by))
        lines.append(f"{IND_SQL_BODY}{TOKEN_FOR_READ_ONLY}")
        lines.extend(self._queryno_lines(spec))
        lines.append(f"{IND_EXEC}{TOKEN_END_EXEC}")

        self._log(
            DECLARATION_MESSAGES["declared_cursor"].format(
                cursor=spec.cursor_name,
                table=spec.table_name,
                count=len(columns),
                queryno=self._queryno(spec.cursor_order),
            )
        )
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

    @staticmethod
    def _conditions(spec: CursorSpec) -> list[str]:
        """De-duplicated predicates, order preserved."""
        out: list[str] = []
        seen: set[str] = set()

        for condition in list(spec.where_conditions or []):
            value = str(condition or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            out.append(value)

        return out

    def _where_lines(self, conditions: list[str]) -> list[str]:
        if not conditions:
            return []

        return [
            f"{IND_SQL_BODY}{TOKEN_WHERE}",
            *self.line_utils.and_lines(
                items=conditions,
                indent=IND_WHERE_NEXT,
            ),
        ]

    def _order_by_columns(
        self,
        spec: CursorSpec,
        has_where: bool,
    ) -> list[str]:
        """ORDER BY entries for one cursor declaration.

        CORRECTION - an entry that is not a column reached the SQL.

        A generated declaration carried

            ORDER BY CT_RKTGDSV_479BFAS
                   , ...
                   , FILLER            <- COBOL placeholder
                   , NR_ID_479BFAS DESC

        FILLER is not a DB2 column, so the DECLARE binds as SQLCODE -206
        and the program never runs. ORDER BY is resolved upstream as free
        text and was rendered unvalidated.

        Every entry is now checked against the cursor's own FROM table,
        exactly as the WHERE ownership guard does. A rejected entry is
        DROPPED and REPORTED - the clause is never fabricated, and one
        bad entry never loses the whole ordering.
        """
        entries = [
            str(column or "").strip()
            for column in list(spec.order_by_columns or [])
            if str(column or "").strip()
        ]

        if not entries:
            self._log(
                DECLARATION_MESSAGES["order_by_none"].format(
                    cursor=spec.cursor_name
                )
            )
            return []

        if ENFORCE_ORDER_BY_COLUMN_OWNERSHIP:
            entries = self._owned_order_by(entries, spec)

            if not entries:
                self._log(
                    DECLARATION_MESSAGES["order_by_all_dropped"].format(
                        cursor=spec.cursor_name
                    )
                )
                return []

        if ENFORCE_ORDER_BY_RETENTION:
            self._log(
                DECLARATION_MESSAGES["order_by_kept"].format(
                    cursor=spec.cursor_name,
                    count=len(entries),
                )
            )
            return entries

        # Legacy path, reachable only when retention is switched off.
        keep = (
            CHILD_CURSOR_KEEPS_ORDER_BY
            if has_where
            else PARENT_CURSOR_KEEPS_ORDER_BY
        )
        if not keep:
            self._log(
                DECLARATION_MESSAGES["order_by_removed"].format(
                    cursor=spec.cursor_name
                )
            )
            return []

        self._log(
            DECLARATION_MESSAGES["order_by_kept"].format(
                cursor=spec.cursor_name,
                count=len(entries),
            )
        )
        return entries

    # =================================================================
    # ORDER BY column ownership
    # =================================================================
    def _owned_order_by(
        self,
        entries: list[str],
        spec: CursorSpec,
    ) -> list[str]:
        """Keep only entries whose COLUMN belongs to the FROM table.

        Stands down when no column list is available, so a missing
        DCLGEN never costs a valid ordering.
        """
        owned = self._owned_columns(spec.table_name)

        kept: list[str] = []
        for entry in entries:
            column = self._order_by_column_name(entry)

            if not column or column.upper() in NON_COLUMN_SENTINELS:
                self._log(
                    DECLARATION_MESSAGES["order_by_column_dropped"].format(
                        entry=entry,
                        cursor=spec.cursor_name,
                        column=column or entry,
                        table=spec.table_name,
                    )
                )
                continue

            if owned and column.upper() not in owned:
                self._log(
                    DECLARATION_MESSAGES["order_by_column_dropped"].format(
                        entry=entry,
                        cursor=spec.cursor_name,
                        column=column,
                        table=spec.table_name,
                    )
                )
                continue

            kept.append(entry)

        return kept

    def _owned_columns(self, table: str) -> set[str]:
        """Uppercased DB2 column names of `table`, or an empty set."""
        if not table or self.column_name_resolver is None:
            return set()

        try:
            columns = self.column_name_resolver.columns_for_table(table)
        except Exception:  # noqa: BLE001
            return set()

        return {
            str(column or "").strip().upper()
            for column in (columns or [])
            if str(column or "").strip()
        }

    @staticmethod
    def _order_by_column_name(entry: str) -> str:
        """The COLUMN part of '<column> [ASC|DESC]'."""
        parts = str(entry or "").strip().split()
        if not parts:
            return ""

        if len(parts) >= 2 and parts[-1].upper() in ORDER_BY_DIRECTIONS:
            parts = parts[:-1]

        return " ".join(parts).strip()
    
    def _order_by_lines(self, columns: list[str]) -> list[str]:
        if not columns:
            return []

        return [
            f"{IND_SQL_BODY}{TOKEN_ORDER_BY}",
            *self.line_utils.comma_lines(
                items=columns,
                indent=IND_WHERE_NEXT,
            ),
        ]

    def _queryno_lines(self, spec: CursorSpec) -> list[str]:
        """QUERYNO clause, derived from the cursor's position.

        The number is DERIVED, never hardcoded, so repeated runs are
        byte-identical and two cursors in the same program can never
        collide:

            QUERYNO_BASE + cursor_order * QUERYNO_STEP
        """
        if not EMIT_QUERYNO:
            return []

        return [
            f"{IND_SQL_BODY}"
            f"{QUERYNO_TEMPLATE.format(number=self._queryno(spec.cursor_order))}"
        ]

    @staticmethod
    def _queryno(order: int) -> int:
        if not EMIT_QUERYNO:
            return 0
        return QUERYNO_BASE + (int(order or 0) * QUERYNO_STEP)

    # =================================================================
    # WHERE column ownership
    # =================================================================
    def _unowned_condition(
        self,
        conditions: list[str],
        table: str,
    ) -> str:
        """First WHERE left operand not owned by `table`.

        A child cursor may only filter on columns of its own FROM table.
        A parent column on the left produces SQLCODE -206 at bind time.
        Returns "" when every predicate is valid, or when no column list
        is available for the table (nothing to validate against).
        """
        if not conditions or not table or self.column_name_resolver is None:
            return ""

        try:
            columns = self.column_name_resolver.columns_for_table(table)
        except Exception:  # noqa: BLE001
            return ""

        owned = {
            str(column or "").strip().upper()
            for column in (columns or [])
            if str(column or "").strip()
        }
        if not owned:
            return ""

        for condition in conditions:
            left = self._left_operand(condition)
            if left and left.upper() not in owned:
                return left

        return ""

    @staticmethod
    def _left_operand(condition: str) -> str:
        text = str(condition or "").strip()
        cut = len(text)

        for token in OPERATOR_TOKENS:
            position = text.find(token)
            if position >= 0:
                cut = min(cut, position)

        return text[:cut].strip()

    # =================================================================
    # Diagnostics
    # =================================================================
    def _log(self, message: str) -> None:
        if message:
            self.messages.append(message)


__all__ = ["CursorDeclareBuilder"]