# LOCATION: tests/test_fetch_error_diagnostics.py
# ACTION: REPLACE ENTIRE FILE
"""The FETCH error branch must identify the failing row.

REGRESSION 1 - no row identity

A parent or single cursor emitted only

    WHEN OTHER
        MOVE 720    TO SQL-LOCATION
        DISPLAY 'ERROR WHILE FETCHING CURSOR DZBFASC1'
        PERFORM SQLERROR

so a production abend could not be tied back to a row. The manual
reference displays the leading fetched columns before PERFORM SQLERROR.

REGRESSION 2 - the two-line wrap was not always enough

IND_WHEN_BODY(11) + "DISPLAY '"(9) + label(18) + "' : ' "(5) costs 43
columns, leaving 22 for the operand. A COBOL data-name may be 30
characters, so the field ALONE could overflow column 72.
"""

import pytest

from idms_db2_phase2.generators.cursor_paragraph.cursor_paragraph_body_builder import (
    CursorParagraphBodyBuilder,
)
from rules.cursor_paragraph_rules import FETCH_KEY_DIAGNOSTIC_LIMIT

CURSOR = "DZBFASC1"
GROUP = "DCLDZBFASTV"
SQL_ERROR = "SQLERROR"
FIELDS = [
    "CT-RKTGDSV-479BFAS",
    "NR-CIOFMAS-479BFAS",
    "DA-CRFMAS-479BFAS",
]
HOSTS = [f":{GROUP}.{field}" for field in FIELDS]

# Body window is columns 8-72, so a body of length n ends at 7 + n.
BODY_END_COLUMN = 72


@pytest.fixture
def paragraphs():
    return CursorParagraphBodyBuilder()


def _bodies(lines: list[str]) -> list[str]:
    return [line.strip() for line in lines if line.strip()]


def _fetch_lines(paragraphs, hosts):
    return paragraphs.fetch_paragraph(
        cursor_name=CURSOR,
        paragraph_name=f"720-FETCH-{CURSOR}",
        host_variables=hosts,
        sql_error_paragraph=SQL_ERROR,
    )


def _fetch(paragraphs, hosts):
    return _bodies(_fetch_lines(paragraphs, hosts))


def _when_other_block(bodies: list[str]) -> list[str]:
    """Statements between WHEN OTHER and END-EVALUATE."""
    start = bodies.index("WHEN OTHER") + 1
    stop = next(
        index for index, body in enumerate(bodies)
        if index > start and body.upper().startswith("END-EVALUATE")
    )
    return bodies[start:stop]


# ---------------------------------------------------------------------
# Order is fixed by the manual reference
# ---------------------------------------------------------------------
def test_sql_location_is_still_the_first_statement(paragraphs):
    """CHK-09.05 / CHK-20.07 read the FIRST statement of the branch."""
    block = _when_other_block(_fetch(paragraphs, HOSTS))

    assert block[0].endswith("TO SQL-LOCATION")


def test_perform_sqlerror_is_still_the_last_statement(paragraphs):
    block = _when_other_block(_fetch(paragraphs, HOSTS))

    assert block[-1] == f"PERFORM {SQL_ERROR}"


def test_diagnostics_sit_between_the_error_text_and_the_perform(paragraphs):
    joined = " ".join(_when_other_block(_fetch(paragraphs, HOSTS)))

    assert (
        joined.index("ERROR WHILE FETCHING")
        < joined.index(FIELDS[0])
        < joined.index(f"PERFORM {SQL_ERROR}")
    )


# ---------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------
def test_every_fetched_column_is_displayed(paragraphs):
    joined = " ".join(_when_other_block(_fetch(paragraphs, HOSTS)))

    for field in FIELDS:
        assert field in joined


def test_each_displayed_host_is_group_qualified(paragraphs):
    """An unqualified DISPLAY operand may not compile."""
    joined = " ".join(_when_other_block(_fetch(paragraphs, HOSTS)))

    assert joined.count(GROUP) >= len(FIELDS)


def test_the_display_list_is_capped(paragraphs):
    many = [f":{GROUP}.CT-COL{index:03d}-479BFAS" for index in range(1, 40)]
    block = _when_other_block(_fetch(paragraphs, many))
    shown = [b for b in block if b.startswith("DISPLAY '") and "CT-COL" in b]

    assert len(shown) <= FETCH_KEY_DIAGNOSTIC_LIMIT


# ---------------------------------------------------------------------
# Host forms and refusals
# ---------------------------------------------------------------------
def test_the_of_host_form_is_accepted(paragraphs):
    """The resolver may deliver 'FIELD OF GROUP'."""
    joined = " ".join(
        _when_other_block(_fetch(paragraphs, [f"{FIELDS[0]} OF {GROUP}"]))
    )

    assert FIELDS[0] in joined
    assert GROUP in joined


def test_an_unqualified_host_is_skipped_not_guessed(paragraphs):
    block = _when_other_block(_fetch(paragraphs, ["WS-UNQUALIFIED-FIELD"]))

    assert not any("WS-UNQUALIFIED-FIELD" in body for body in block)
    assert block[0].endswith("TO SQL-LOCATION")
    assert block[-1] == f"PERFORM {SQL_ERROR}"


def test_no_hosts_leaves_the_generic_branch_intact(paragraphs):
    block = _when_other_block(_fetch(paragraphs, []))

    assert block[0].endswith("TO SQL-LOCATION")
    assert any("ERROR WHILE FETCHING" in body for body in block)
    assert block[-1] == f"PERFORM {SQL_ERROR}"


# ---------------------------------------------------------------------
# Open and close are untouched
# ---------------------------------------------------------------------
def test_open_and_close_gain_no_diagnostics(paragraphs):
    """Only FETCH has a fetched row worth reporting."""
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
        joined = " ".join(_when_other_block(_bodies(lines)))
        assert not any(field in joined for field in FIELDS)


# ---------------------------------------------------------------------
# Fixed-format width
# ---------------------------------------------------------------------
def test_no_generated_body_line_passes_column_72(paragraphs):
    """A DISPLAY that overflows is wrapped, never truncated."""
    field = "DA-VERYLONGCOLUMNNAME-479BFAS"

    for line in _fetch_lines(paragraphs, [f":{GROUP}.{field}"]):
        assert 7 + len(line) <= BODY_END_COLUMN, f"overflow: {line!r}"


def test_a_maximum_length_name_never_overflows(paragraphs):
    """A COBOL data-name may be 30 characters."""
    field = "D" + "A" * 29

    for line in _fetch_lines(paragraphs, [f":{GROUP}.{field}"]):
        assert 7 + len(line) <= BODY_END_COLUMN, f"overflow: {line!r}"


def test_a_long_host_keeps_its_full_name(paragraphs):
    """Truncation would produce an undefined data-name."""
    field = "DA-VERYLONGCOLUMNNAME-479BFAS"
    joined = " ".join(
        _when_other_block(_fetch(paragraphs, [f":{GROUP}.{field}"]))
    )

    assert field in joined
    assert GROUP in joined


def test_a_long_host_wraps_onto_three_lines(paragraphs):
    """43 fixed columns leave 22 for the operand; this one needs 29."""
    field = "DA-VERYLONGCOLUMNNAME-479BFAS"
    block = _when_other_block(_fetch(paragraphs, [f":{GROUP}.{field}"]))

    literal = [b for b in block if b.startswith("DISPLAY '")]
    operand = [b for b in block if b == field]
    qualifier = [b for b in block if b == f"OF {GROUP}"]

    assert len(literal) == 2       # generic error text + the key literal
    assert len(operand) == 1
    assert len(qualifier) == 1