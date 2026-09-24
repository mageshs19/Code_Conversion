# LOCATION: tests/test_cursor_generation_contract.py
# ACTION: CREATE NEW FILE

"""Contract tests for the generated cursor block.

Each test pins one defect that reached a production-shaped output and was
fixed. They are unit tests on the builders - no Sheet Mapping, no DCLGEN,
no file I/O - so they run in milliseconds and fail for exactly one reason.

REGRESSION 1 - stale host data after a non-zero SQLCODE
--------------------------------------------------------
DB2 leaves the host variables UNCHANGED when a FETCH returns SQLCODE 100
or a negative code. Without INITIALIZE the DCLGEN group still holds the
PREVIOUS row and every downstream MOVE ... OF <group> copies stale values
into the output record.

REGRESSION 2 - SQLERROR reported a stale location
--------------------------------------------------
SQLERROR displays SQL-LOCATION. Setting it only at paragraph entry lets
any statement in between leave a stale value, sending the operator to the
wrong paragraph.

REGRESSION 3 - no QUERYNO on the DECLARE
-----------------------------------------
DB2 EXPLAIN identifies a statement by QUERYNO. Without one, an access
path cannot be tied back to the cursor that produced it.
"""

from __future__ import annotations

import pytest

from idms_db2_phase2.generators.cursor_paragraph.cursor_paragraph_body_builder import (
    CursorParagraphBodyBuilder,
)
from idms_db2_phase2.generators.db2_infrastructure.cursor_declare_builder import (
    CursorDeclareBuilder,
)
from idms_db2_phase2.generators.db2_infrastructure.cursor_spec import CursorSpec
from rules.cursor_declaration_rules import QUERYNO_BASE, QUERYNO_STEP

CURSOR = "DZBFASC1"
GROUP = "DCLDZBFASTV"
SQL_ERROR = "SQLERROR"

HOSTS = [
    f":{GROUP}.DA-CPTAFS-479BFAS",
    f":{GROUP}.DA-CRFMAS-479BFAS",
]


# =====================================================================
# Helpers
# =====================================================================
def _bodies(lines: list[str]) -> list[str]:
    """Non-blank lines, trimmed. Indentation is not under test here."""
    return [line.strip() for line in lines if line.strip()]


class _LineUtils:
    """Minimal stand-in for the infrastructure line utils.

    Only the two list renderers the declare builder calls are needed.
    Using a stub keeps the test independent of fixed-format geometry.
    """

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


@pytest.fixture
def paragraphs() -> CursorParagraphBodyBuilder:
    return CursorParagraphBodyBuilder()


@pytest.fixture
def declares() -> CursorDeclareBuilder:
    return CursorDeclareBuilder(_LineUtils())


def _spec(order: int = 0, **overrides) -> CursorSpec:
    source = {
        "cursor_name": CURSOR,
        "table_name": "DZBFASTV",
        "record_name": "VMBFAS",
        "select_columns": ["DA_CPTAFS_479BFAS", "DA_CRFMAS_479BFAS"],
        "cursor_order": order,
    }
    source.update(overrides)
    return CursorSpec.read(source)


# =====================================================================
# REGRESSION 1 - FETCH prologue
# =====================================================================
def test_fetch_paragraph_initializes_the_dclgen_group(paragraphs):
    bodies = _bodies(
        paragraphs.fetch_paragraph(
            cursor_name=CURSOR,
            paragraph_name=f"720-FETCH-{CURSOR}",
            host_variables=HOSTS,
            sql_error_paragraph=SQL_ERROR,
        )
    )

    assert f"INITIALIZE {GROUP}." in bodies


def test_fetch_paragraph_rearms_the_not_eoc_flag(paragraphs):
    bodies = _bodies(
        paragraphs.fetch_paragraph(
            cursor_name=CURSOR,
            paragraph_name=f"720-FETCH-{CURSOR}",
            host_variables=HOSTS,
            sql_error_paragraph=SQL_ERROR,
        )
    )

    assert f"SET {CURSOR}-NOT-EOC TO TRUE" in bodies


def test_fetch_prologue_runs_before_the_fetch(paragraphs):
    """An INITIALIZE after the FETCH would erase the row just read."""
    bodies = _bodies(
        paragraphs.fetch_paragraph(
            cursor_name=CURSOR,
            paragraph_name=f"720-FETCH-{CURSOR}",
            host_variables=HOSTS,
            sql_error_paragraph=SQL_ERROR,
        )
    )

    initialize = bodies.index(f"INITIALIZE {GROUP}.")
    fetch = bodies.index(f"FETCH {CURSOR}")

    assert initialize < fetch


def test_host_group_is_read_from_the_of_form(paragraphs):
    """The resolver may deliver 'HOST OF GROUP' instead of ':GROUP.HOST'."""
    bodies = _bodies(
        paragraphs.fetch_paragraph(
            cursor_name=CURSOR,
            paragraph_name=f"720-FETCH-{CURSOR}",
            host_variables=[f"DA-CPTAFS-479BFAS OF {GROUP}"],
            sql_error_paragraph=SQL_ERROR,
        )
    )

    assert f"INITIALIZE {GROUP}." in bodies


def test_no_empty_initialize_when_the_group_cannot_be_derived(paragraphs):
    """'INITIALIZE .' is invalid COBOL. Omit the statement instead."""
    bodies = _bodies(
        paragraphs.fetch_paragraph(
            cursor_name=CURSOR,
            paragraph_name=f"720-FETCH-{CURSOR}",
            host_variables=["WS-UNQUALIFIED-FIELD"],
            sql_error_paragraph=SQL_ERROR,
        )
    )

    assert not any(body.startswith("INITIALIZE") for body in bodies)
    assert f"SET {CURSOR}-NOT-EOC TO TRUE" in bodies


def test_open_and_close_paragraphs_gain_no_initialize(paragraphs):
    """Only FETCH populates host variables; the others must not clear them."""
    for lines in (
        paragraphs.open_paragraph(
            cursor_name=CURSOR,
            paragraph_name=f"710-OPEN-{CURSOR}",
            sql_error_paragraph=SQL_ERROR,
        ),
        paragraphs.close_paragraph(
            cursor_name=CURSOR,
            paragraph_name=f"730-CLOSE-{CURSOR}",
            sql_error_paragraph=SQL_ERROR,
        ),
    ):
        assert not any(
            body.startswith("INITIALIZE") for body in _bodies(lines)
        )


# =====================================================================
# REGRESSION 2 - SQL-LOCATION in the error branch
# =====================================================================
def _when_other_body(bodies: list[str]) -> str:
    """First statement of the WHEN OTHER branch."""
    return bodies[bodies.index("WHEN OTHER") + 1]


def test_open_error_branch_sets_sql_location(paragraphs):
    bodies = _bodies(
        paragraphs.open_paragraph(
            cursor_name=CURSOR,
            paragraph_name=f"710-OPEN-{CURSOR}",
            sql_error_paragraph=SQL_ERROR,
        )
    )

    assert _when_other_body(bodies).endswith("TO SQL-LOCATION")


def test_fetch_error_branch_sets_sql_location(paragraphs):
    bodies = _bodies(
        paragraphs.fetch_paragraph(
            cursor_name=CURSOR,
            paragraph_name=f"720-FETCH-{CURSOR}",
            host_variables=HOSTS,
            sql_error_paragraph=SQL_ERROR,
        )
    )

    assert _when_other_body(bodies).endswith("TO SQL-LOCATION")


def test_close_error_branch_sets_sql_location(paragraphs):
    bodies = _bodies(
        paragraphs.close_paragraph(
            cursor_name=CURSOR,
            paragraph_name=f"730-CLOSE-{CURSOR}",
            sql_error_paragraph=SQL_ERROR,
        )
    )

    assert _when_other_body(bodies).endswith("TO SQL-LOCATION")


def test_entry_point_sql_location_is_still_emitted(paragraphs):
    """CHK-09.05 requires SQL-LOCATION set BEFORE the retrieval."""
    bodies = _bodies(
        paragraphs.fetch_paragraph(
            cursor_name=CURSOR,
            paragraph_name=f"720-FETCH-{CURSOR}",
            host_variables=HOSTS,
            sql_error_paragraph=SQL_ERROR,
        )
    )

    moves = [body for body in bodies if body.endswith("TO SQL-LOCATION")]

    assert len(moves) == 2, "expected one at paragraph entry, one in WHEN OTHER"
    assert bodies.index(moves[0]) < bodies.index("EXEC SQL")


def test_paragraph_is_one_sentence(paragraphs):
    """A period inside EVALUATE closes the scope and orphans END-EVALUATE."""
    bodies = _bodies(
        paragraphs.fetch_paragraph(
            cursor_name=CURSOR,
            paragraph_name=f"720-FETCH-{CURSOR}",
            host_variables=HOSTS,
            sql_error_paragraph=SQL_ERROR,
        )
    )

    assert bodies[-1] == "."
    assert bodies.count(".") == 1


# =====================================================================
# REGRESSION 3 - QUERYNO on the DECLARE
# =====================================================================
def test_declaration_carries_a_queryno(declares):
    bodies = _bodies(declares.build(_spec(order=0)))

    assert any(body.startswith("QUERYNO ") for body in bodies)


def test_queryno_is_the_last_clause_before_end_exec(declares):
    """SQL clause order is fixed: ... FOR READ ONLY, QUERYNO, END-EXEC."""
    bodies = _bodies(declares.build(_spec(order=0)))

    assert bodies[-1] == "END-EXEC."
    assert bodies[-2].startswith("QUERYNO ")
    assert bodies[-3] == "FOR READ ONLY"


def test_queryno_is_derived_from_the_cursor_order(declares):
    bodies = _bodies(declares.build(_spec(order=2)))
    expected = QUERYNO_BASE + (2 * QUERYNO_STEP)

    assert f"QUERYNO {expected}" in bodies


def test_two_cursors_never_share_a_queryno(declares):
    first = _bodies(declares.build(_spec(order=0)))
    second = _bodies(declares.build(_spec(order=1)))

    def queryno(bodies: list[str]) -> str:
        return next(b for b in bodies if b.startswith("QUERYNO "))

    assert queryno(first) != queryno(second)


def test_queryno_is_stable_across_runs(declares):
    """Byte-identical output on repeated runs is a release requirement."""
    assert declares.build(_spec(order=1)) == declares.build(_spec(order=1))


def test_a_child_cursor_keeps_where_and_order_by(declares):
    """Proves the clause order is unchanged once WHERE/ORDER BY exist."""
    spec = _spec(
        order=0,
        where_conditions=["NR_CIO_479BFAS = :DCLPARENT.NR-CIO"],
        order_by_columns=["NR_ID_479BFAS ASC"],
    )
    bodies = _bodies(declares.build(spec))

    assert bodies.index("WHERE") < bodies.index("ORDER BY")
    assert bodies.index("ORDER BY") < bodies.index("FOR READ ONLY")
    assert bodies[-2].startswith("QUERYNO ")


def test_a_spec_without_a_table_produces_a_warning_not_sql(declares):
    """Refusing beats guessing: no fabricated FROM clause."""
    bodies = _bodies(declares.build(_spec(order=0, table_name="")))

    assert len(bodies) == 1
    assert "DB2 WARNING" in bodies[0]


# =====================================================================
# CursorSpec - order must survive, and never collide
# =====================================================================
def test_cursor_order_is_read_from_the_spec_dict():
    assert CursorSpec.read({"cursor_name": CURSOR, "cursor_order": 3}).cursor_order == 3


def test_missing_cursor_order_falls_back_to_list_position():
    """Two cursors sharing an order would share a QUERYNO."""
    specs = CursorSpec.read_all(
        [{"cursor_name": "C1"}, {"cursor_name": "C2"}]
    )

    assert [spec.cursor_order for spec in specs] == [0, 1]


def test_a_malformed_cursor_order_never_raises():
    assert CursorSpec.read({"cursor_order": "not-a-number"}, 7).cursor_order == 7
    assert CursorSpec.read({"cursor_order": -1}, 4).cursor_order == 4