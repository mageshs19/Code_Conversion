# LOCATION: tests/test_cursor_order_by_retention.py
# ACTION: REPLACE ENTIRE FILE
"""ORDER BY must survive on every cursor.

REGRESSION - a resolved ORDER BY was deleted

CursorDeclareBuilder dropped ORDER BY from any cursor with no WHERE, and
CursorOrderCleanupComposer stripped it again from the rendered text. Two
independent strippers for one clause.

Manual reference VMDZ7200 (Train Case 3) ends its ROOT cursor with

    ORDER BY NR_ID_479BFAS ASC
    FOR READ ONLY
    QUERYNO 254

Row sequence is business meaning: the extract file inherits it.

NOTE - CursorDeclareBuilder.build() takes a CursorSpec, never a dict.
Db2InfrastructureGenerator builds plain dicts and CursorSpec.read()
normalises them, so the fixture below goes through the same door the
production path uses.
"""

from __future__ import annotations

import pytest

from idms_db2_phase2.composers.cursor_order_cleanup_composer import (
    CursorOrderCleanupComposer,
)
from idms_db2_phase2.generators.db2_infrastructure.cursor_declare_builder import (
    CursorDeclareBuilder,
)
from idms_db2_phase2.generators.db2_infrastructure.cursor_spec import CursorSpec
from rules.cursor_declaration_rules import (
    CHILD_CURSOR_KEEPS_ORDER_BY,
    ENFORCE_ORDER_BY_RETENTION,
    PARENT_CURSOR_KEEPS_ORDER_BY,
)
from rules.cursor_order_cleanup_rules import (
    ENFORCE_PARENT_CURSOR_ORDER_BY_CLEANUP,
)

CURSOR = "DZBFASC1"
TABLE = "DZBFASTV"
RECORD = "VMBFAS"
ORDER_COLUMN = "NR_ID_479BFAS ASC"
PREDICATE = "NR_CIOFMAS_479BFAS = :DCLDZBSIASTV.NR-CIOFMAS"


# =====================================================================
# Helpers
# =====================================================================
class _LineUtils:
    """Minimal stand-in for the infrastructure line utils."""

    @staticmethod
    def and_lines(items: list[str], indent: str) -> list[str]:
        return [
            f"{indent}{'AND ' if index else ''}{item}"
            for index, item in enumerate(items)
        ]

    @staticmethod
    def comma_lines(items: list[str], indent: str) -> list[str]:
        return [
            f"{indent}{', ' if index else ''}{item}"
            for index, item in enumerate(items)
        ]


def _bodies(lines: list[str]) -> list[str]:
    """Non-blank lines, trimmed. Indentation is not under test here."""
    return [line.strip() for line in lines if line.strip()]


def _clause_index(bodies: list[str], token: str) -> int:
    for index, body in enumerate(bodies):
        if body.upper().startswith(token):
            return index
    return -1


def _has_clause(bodies: list[str], token: str) -> bool:
    return _clause_index(bodies, token) >= 0


def _spec(
    where=None,
    order_by=None,
    order: int = 0,
) -> CursorSpec:
    """A spec dict exactly as CursorSpecBuilder emits it, then read."""
    return CursorSpec.read(
        {
            "cursor_name": CURSOR,
            "table_name": TABLE,
            "record_name": RECORD,
            "select_columns": ["CT_RKTGDSV_479BFAS", "NR_ID_479BFAS"],
            "where_conditions": list(where or []),
            "order_by_columns": list(order_by or []),
            "cursor_order": order,
        }
    )


@pytest.fixture
def declares() -> CursorDeclareBuilder:
    return CursorDeclareBuilder(_LineUtils())


# =====================================================================
# Rule state
# =====================================================================
def test_retention_is_the_site_standard():
    assert ENFORCE_ORDER_BY_RETENTION is True
    assert PARENT_CURSOR_KEEPS_ORDER_BY is True
    assert CHILD_CURSOR_KEEPS_ORDER_BY is True


def test_the_cleanup_pass_is_disabled():
    assert ENFORCE_PARENT_CURSOR_ORDER_BY_CLEANUP is False


# =====================================================================
# Declare builder
# =====================================================================
def test_a_root_cursor_keeps_order_by(declares):
    """The manual reference orders its root cursor."""
    bodies = _bodies(declares.build(_spec(order_by=[ORDER_COLUMN])))

    assert _has_clause(bodies, "ORDER BY")
    assert any(ORDER_COLUMN in body for body in bodies)


def test_a_child_cursor_keeps_order_by(declares):
    bodies = _bodies(
        declares.build(_spec(where=[PREDICATE], order_by=[ORDER_COLUMN]))
    )

    assert _has_clause(bodies, "ORDER BY")


def test_clause_order_is_unchanged(declares):
    """SELECT, FROM, WHERE, ORDER BY, FOR READ ONLY, QUERYNO."""
    bodies = _bodies(
        declares.build(_spec(where=[PREDICATE], order_by=[ORDER_COLUMN]))
    )

    assert _clause_index(bodies, "FROM") < _clause_index(bodies, "WHERE")
    assert _clause_index(bodies, "WHERE") < _clause_index(bodies, "ORDER BY")
    assert _clause_index(bodies, "ORDER BY") < _clause_index(
        bodies, "FOR READ ONLY"
    )
    assert bodies[-2].upper().startswith("QUERYNO ")
    assert bodies[-1].upper().startswith("END-EXEC")


def test_no_order_by_columns_is_reported_not_silent(declares):
    declares.build(_spec(order_by=[]))

    assert any("no resolvable ORDER BY" in m for m in declares.messages)


def test_a_kept_order_by_is_reported(declares):
    declares.build(_spec(order_by=[ORDER_COLUMN]))

    assert any("keeps ORDER BY" in m for m in declares.messages)


def test_order_by_is_never_removed(declares):
    declares.build(_spec(order_by=[ORDER_COLUMN]))

    assert not any("removed ORDER BY" in m for m in declares.messages)


def test_a_cursor_without_order_by_renders_valid_sql(declares):
    """No ORDER BY columns must not break the clause sequence."""
    bodies = _bodies(declares.build(_spec(order_by=[])))

    assert not _has_clause(bodies, "ORDER BY")
    assert _has_clause(bodies, "FOR READ ONLY")
    assert bodies[-1].upper().startswith("END-EXEC")


# =====================================================================
# Cleanup composer
# =====================================================================
def _declare_text() -> str:
    return "\n".join(
        [
            "      EXEC SQL",
            f"        DECLARE {CURSOR} CURSOR WITH HOLD FOR",
            "        SELECT  CT_RKTGDSV_479BFAS",
            "              , NR_ID_479BFAS",
            f"        FROM    {TABLE}",
            f"        ORDER BY {ORDER_COLUMN}",
            "        FOR READ ONLY",
            "        QUERYNO 710",
            "      END-EXEC.",
        ]
    )


def test_the_composer_is_a_no_op():
    source = _declare_text()

    assert CursorOrderCleanupComposer().compose(source) == source


def test_the_composer_reports_that_it_is_disabled():
    composer = CursorOrderCleanupComposer()
    composer.compose(_declare_text())

    assert any("pass disabled" in m for m in composer.messages)


def test_the_composer_never_strips_order_by():
    result = CursorOrderCleanupComposer().compose(_declare_text())

    assert "ORDER BY" in result
    assert ORDER_COLUMN in result


def test_empty_text_is_safe():
    assert CursorOrderCleanupComposer().compose("") == ""