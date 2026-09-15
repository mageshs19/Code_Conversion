# LOCATION: src/idms_db2_phase2/generators/cursor_declaration_generator.py
# ACTION: REPLACE ENTIRE FILE

"""Generates DB2 cursor DECLARE statements.

Emits the COBOL team's manual reference layout exactly:

    * DECLARE CURSOR FOR BEFF TABLE
    * ------------------------------
    *
        EXEC SQL DECLARE DZBEFFC1 CURSOR WITH HOLD FOR
          SELECT CO_IDPRKSK_479BEFF
               , NS_IRMOSTK_479BEFF
               , DA_UBSECIS_479BEFF
          FROM DZBEFFTV
          FOR READ ONLY
                 QUERYNO 176
        END-EXEC

Authority and safety rules honoured here:

- A cursor with NO WHERE clause is a parent/root cursor and never carries
  ORDER BY (matches composers/cursor_order_cleanup_composer.py).
- A cursor WITH a WHERE clause is a child/dependent cursor and keeps its
  ORDER BY.
- The left operand of every WHERE predicate must be a column of the
  cursor's own FROM table. A parent column on the left binds as
  SQLCODE -206, so the declaration is refused and reported instead.
- Nothing is fabricated when Sheet Mapping or DCLGEN metadata is missing;
  a DB2 WARNING comment is emitted (CONVERSION_RULES).

Clean Architecture:
- Every literal lives in rules/cursor_declaration_rules.py and
  rules/manual_reference_rules.py.
- No regex is defined in this file.
- No program, record, table, cursor or host variable name is hardcoded.
"""

from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.cursor_declaration_rules import (
    CHILD_CURSOR_KEEPS_ORDER_BY,
    DECLARATION_MESSAGES,
    DECLARE_LINE_TEMPLATE,
    DECLARE_ON_EXEC_SQL_LINE,
    EMIT_QUERYNO,
    END_EXEC,
    ENFORCE_WHERE_COLUMN_OWNERSHIP,
    FOR_READ_ONLY,
    FROM_TEMPLATE,
    IND_CLAUSE,
    IND_EXEC,
    IND_QUERYNO,
    IND_SELECT_FIRST,
    IND_SELECT_NEXT,
    IND_WHERE_NEXT,
    LAST_DECLARATION_TERMINATOR,
    ORDER_BY_TEMPLATE,
    PARENT_CURSOR_KEEPS_ORDER_BY,
    QUERYNO_BASE,
    QUERYNO_STEP,
    QUERYNO_TEMPLATE,
    SELECT_FIRST_TEMPLATE,
    SELECT_NEXT_TEMPLATE,
    UNRESOLVED_JOIN_KEY_TEMPLATE,
    WHERE_FIRST_TEMPLATE,
    WHERE_NEXT_TEMPLATE,
)
from rules.manual_reference_rules import (
    CURSOR_BANNER_BLANK,
    CURSOR_BANNER_TITLE_TEMPLATE,
    CURSOR_BANNER_UNDERLINE,
)

# Warning text used when the spec itself is unusable.
MISSING_CURSOR_NAME = (
    "* DB2 WARNING: Unable to declare cursor; missing cursor name."
)
MISSING_TABLE_TEMPLATE = (
    "* DB2 WARNING: Unable to declare cursor {cursor}; "
    "missing DB2 table mapping."
)
MISSING_COLUMNS_TEMPLATE = (
    "* DB2 WARNING: Unable to declare cursor {cursor}; "
    "no DB2 columns resolved for table {table}."
)

# Table-name affixes stripped when deriving the short banner name.
TABLE_SUFFIXES = ("_TV", "_TB")
TABLE_SHORT_SUFFIXES = ("TV", "TB")
TABLE_PREFIX_LENGTH = 2


class CursorDeclarationGenerator:
    """Builds the WORKING-STORAGE cursor declaration block."""

    def __init__(
        self,
        column_name_resolver,
        diagnostics: list[str] | None = None,
    ) -> None:
        self.column_name_resolver = column_name_resolver
        self.messages: list[str] = diagnostics if diagnostics is not None else []

    # =================================================================
    # Public entry point
    # =================================================================
    def generate(
        self,
        specs: list[dict[str, object]],
    ) -> list[str]:
        """Render every cursor declaration, in cursor order.

        Returns a flat list of COBOL body lines (no sequence numbers).
        The fixed-format writer applies columns 1-6, 7 and 73-80.
        """
        self.messages = []

        if not specs:
            return []

        lines: list[str] = []
        total = len(specs)

        for index, spec in enumerate(specs):
            block = self._declaration(
                spec=spec,
                order=index,
                is_last=index == total - 1,
            )
            if not block:
                continue
            if lines:
                lines.append("")
            lines.extend(block)

        return lines

    # =================================================================
    # One declaration
    # =================================================================
    def _declaration(
        self,
        spec: dict[str, object],
        order: int,
        is_last: bool,
    ) -> list[str]:
        cursor = NameNormalizer.to_cobol(str(spec.get("cursor_name", "")))
        if not cursor:
            return [MISSING_CURSOR_NAME]

        table = NameNormalizer.normalize(str(spec.get("table_name", "")))
        if not table:
            return [MISSING_TABLE_TEMPLATE.format(cursor=cursor)]

        columns = self._columns(spec)
        if not columns:
            return [
                MISSING_COLUMNS_TEMPLATE.format(cursor=cursor, table=table)
            ]

        conditions = self._where_conditions(spec)

        if ENFORCE_WHERE_COLUMN_OWNERSHIP and conditions:
            unowned = self._unowned_condition(conditions, table)
            if unowned:
                self._log(
                    DECLARATION_MESSAGES["join_key_unresolved"].format(
                        column=unowned,
                        table=table,
                        cursor=cursor,
                    )
                )
                return [
                    UNRESOLVED_JOIN_KEY_TEMPLATE.format(
                        cursor=cursor,
                        column=unowned,
                        table=table,
                    )
                ]

        order_by = self._order_by(
            spec=spec,
            has_where=bool(conditions),
            cursor=cursor,
        )
        queryno = self._queryno(order)

        lines: list[str] = []
        lines.extend(self._banner(table))
        lines.extend(
            self._body(
                cursor=cursor,
                table=table,
                columns=columns,
                conditions=conditions,
                order_by=order_by,
                queryno=queryno,
                is_last=is_last,
            )
        )

        self._log(
            DECLARATION_MESSAGES["declared_cursor"].format(
                cursor=cursor,
                table=table,
                count=len(columns),
                queryno=queryno,
            )
        )
        return lines

    # =================================================================
    # Banner
    # =================================================================
    def _banner(self, table: str) -> list[str]:
        return [
            CURSOR_BANNER_TITLE_TEMPLATE.format(
                short_name=self._short_table_name(table)
            ),
            CURSOR_BANNER_UNDERLINE,
            CURSOR_BANNER_BLANK,
        ]

    @staticmethod
    def _short_table_name(table: str) -> str:
        """DZBEFFTV -> BEFF. Prefix and TV/TB suffix removed."""
        token = NameNormalizer.normalize(str(table or ""))
        if not token:
            return ""

        for suffix in TABLE_SUFFIXES:
            if token.endswith(suffix):
                token = token[: -len(suffix)]
                break
        else:
            for suffix in TABLE_SHORT_SUFFIXES:
                if token.endswith(suffix):
                    token = token[: -len(suffix)]
                    break

        if len(token) > TABLE_PREFIX_LENGTH:
            token = token[TABLE_PREFIX_LENGTH:]

        return token.strip("_-") or NameNormalizer.normalize(table)

    # =================================================================
    # SQL body
    # =================================================================
    def _body(
        self,
        cursor: str,
        table: str,
        columns: list[str],
        conditions: list[str],
        order_by: list[str],
        queryno: int,
        is_last: bool,
    ) -> list[str]:
        lines: list[str] = []

        # --- EXEC SQL DECLARE ---------------------------------------
        declare = DECLARE_LINE_TEMPLATE.format(cursor=cursor)
        if DECLARE_ON_EXEC_SQL_LINE:
            lines.append(f"{IND_EXEC}{declare}")
        else:
            lines.append(f"{IND_EXEC}EXEC SQL")
            lines.append(f"{IND_CLAUSE}DECLARE {cursor} CURSOR WITH HOLD FOR")

        # --- SELECT column list -------------------------------------
        for position, column in enumerate(columns):
            if position == 0:
                lines.append(
                    f"{IND_SELECT_FIRST}"
                    f"{SELECT_FIRST_TEMPLATE.format(column=column)}"
                )
            else:
                lines.append(
                    f"{IND_SELECT_NEXT}"
                    f"{SELECT_NEXT_TEMPLATE.format(column=column)}"
                )

        # --- FROM ----------------------------------------------------
        lines.append(f"{IND_CLAUSE}{FROM_TEMPLATE.format(table=table)}")

        # --- WHERE / AND ---------------------------------------------
        for position, condition in enumerate(conditions):
            if position == 0:
                lines.append(
                    f"{IND_CLAUSE[:-1]}"
                    f"{WHERE_FIRST_TEMPLATE.format(condition=condition)}"
                )
            else:
                lines.append(
                    f"{IND_WHERE_NEXT}"
                    f"{WHERE_NEXT_TEMPLATE.format(condition=condition)}"
                )

        # --- ORDER BY -------------------------------------------------
        if order_by:
            lines.append(
                f"{IND_CLAUSE}"
                f"{ORDER_BY_TEMPLATE.format(columns=' '.join(order_by))}"
            )

        # --- FOR READ ONLY -------------------------------------------
        lines.append(f"{IND_CLAUSE}{FOR_READ_ONLY}")

        # --- QUERYNO --------------------------------------------------
        if queryno:
            lines.append(
                f"{IND_QUERYNO}{QUERYNO_TEMPLATE.format(number=queryno)}"
            )

        # --- END-EXEC -------------------------------------------------
        terminator = LAST_DECLARATION_TERMINATOR if is_last else ""
        lines.append(f"{IND_EXEC}{END_EXEC}{terminator}")

        return lines

    # =================================================================
    # Spec helpers
    # =================================================================
    @staticmethod
    def _columns(spec: dict[str, object]) -> list[str]:
        """Normalised SELECT column list, order preserved, de-duplicated.

        Column order is authoritative: the FETCH INTO host list is built
        from the same sequence, so a mismatch here silently corrupts data.
        """
        out: list[str] = []
        seen: set[str] = set()

        for column in list(spec.get("select_columns", []) or []):
            value = NameNormalizer.normalize(str(column))
            if not value or value in seen:
                continue
            seen.add(value)
            out.append(value)

        return out

    @staticmethod
    def _where_conditions(spec: dict[str, object]) -> list[str]:
        """Join predicates, already built by CursorJoinResolver."""
        out: list[str] = []
        seen: set[str] = set()

        for condition in list(spec.get("where_conditions", []) or []):
            value = str(condition or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            out.append(value)

        return out

    def _order_by(
        self,
        spec: dict[str, object],
        has_where: bool,
        cursor: str,
    ) -> list[str]:
        """ORDER BY survives on child cursors only.

        A cursor with no WHERE clause is a parent/root cursor. The manual
        reference never orders a parent cursor, so any ORDER BY resolved
        upstream is dropped here and reported.
        """
        columns = [
            str(column or "").strip()
            for column in list(spec.get("order_by_columns", []) or [])
            if str(column or "").strip()
        ]
        if not columns:
            return []

        keep = (
            CHILD_CURSOR_KEEPS_ORDER_BY
            if has_where
            else PARENT_CURSOR_KEEPS_ORDER_BY
        )
        if not keep:
            self._log(
                DECLARATION_MESSAGES["order_by_removed"].format(cursor=cursor)
            )
            return []

        return columns

    @staticmethod
    def _queryno(order: int) -> int:
        """Stable QUERYNO so repeated runs are byte-identical."""
        if not EMIT_QUERYNO:
            return 0
        return QUERYNO_BASE + (order * QUERYNO_STEP)

    # =================================================================
    # WHERE column ownership
    # =================================================================
    def _unowned_condition(
        self,
        conditions: list[str],
        table: str,
    ) -> str:
        """Return the first WHERE left operand not owned by `table`.

        A child cursor may only filter on columns of its own FROM table.
        A parent column on the left produces SQLCODE -206 at bind time.
        Returns "" when every predicate is valid, or when DCLGEN has no
        column list for the table (nothing to validate against).
        """
        owned = {
            NameNormalizer.normalize(str(column)).upper()
            for column in self.column_name_resolver.columns_for_table(table)
        }
        owned.discard("")

        if not owned:
            return ""

        for condition in conditions:
            left = condition.split("=", 1)[0].strip().upper()
            if left and left not in owned:
                return left

        return ""

    # =================================================================
    # Diagnostics
    # =================================================================
    def _log(self, message: str) -> None:
        if message:
            self.messages.append(message)