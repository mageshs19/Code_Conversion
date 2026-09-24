# LOCATION: tests/test_marker_banner_width.py
# ACTION: REPLACE ENTIRE FILE
"""Generated marker banners must fit the fixed-format body window.

REGRESSION

DB2_INFRASTRUCTURE_MARKER is 69 characters. The banner template pads
with {title:<62} but never truncates, so the rendered banner ran past
column 72 and the fixed-format writer wrapped it:

    002350*DB2 SQLCA, SQL ERROR WORKING STORAGE, DCLGEN INCLUDES, AND CURSOR
    002360*FLAGS*

The phrase was split and the second line carried no opening asterisk.

TEST ISOLATION

The banner template is declared locally rather than imported. What is
under test is the TITLE SELECTION made by InfrastructureBlockBuilder,
not the renderer that formats it. Importing the real template would
couple this test to a constant owned by another module and would break
collection if that module is reorganised - which is exactly what
happened on the first two attempts at this file.
"""

import pytest

from catalogs.output_sections import (
    COMMENT_BODY_WIDTH,
    COMMENT_TITLE_WIDTH,
    DB2_CURSOR_DECLARATIONS_MARKER,
    DB2_CURSOR_FLAGS_MARKER,
    DB2_INFRASTRUCTURE_MARKER,
    DB2_INFRASTRUCTURE_MARKER_SHORT,
)
from idms_db2_phase2.generators.db2_infrastructure.infrastructure_block_builder import (
    InfrastructureBlockBuilder,
)

# Mirrors the production banner shape. Local by design - see TEST ISOLATION.
BANNER_TEMPLATE = "*{title:<62}*"

MARKERS_UNDER_TEST = [
    DB2_INFRASTRUCTURE_MARKER,
    DB2_CURSOR_FLAGS_MARKER,
    DB2_CURSOR_DECLARATIONS_MARKER,
]


class _LineUtils:
    """Minimal stand-in for the injected infrastructure line utils."""

    @staticmethod
    def comment_block(title: str) -> list[str]:
        return [BANNER_TEMPLATE.format(title=title)]

    @staticmethod
    def and_lines(items: list[str], indent: str) -> list[str]:
        return [f"{indent}{item}" for item in items]

    @staticmethod
    def comma_lines(items: list[str], indent: str) -> list[str]:
        return [f"{indent}{item}" for item in items]

    @staticmethod
    def normalize_include_name(value: str) -> str:
        return str(value or "").strip().upper()

    @staticmethod
    def logical(line: str) -> str:
        return str(line or "").strip()


@pytest.fixture
def builder():
    return InfrastructureBlockBuilder(_LineUtils())


# ---------------------------------------------------------------------
# Title selection - the actual contract
# ---------------------------------------------------------------------
@pytest.mark.parametrize("marker", MARKERS_UNDER_TEST)
def test_every_chosen_title_fits_the_banner_window(builder, marker):
    """Template independent: the TITLE itself must fit."""
    assert len(builder._fit_marker(marker)) <= COMMENT_TITLE_WIDTH


def test_the_long_infrastructure_marker_uses_its_short_form(builder):
    """The 69-character marker is the one that overflowed."""
    assert len(DB2_INFRASTRUCTURE_MARKER) > COMMENT_TITLE_WIDTH

    assert builder._fit_marker(DB2_INFRASTRUCTURE_MARKER) == (
        DB2_INFRASTRUCTURE_MARKER_SHORT
    )


def test_a_marker_that_already_fits_is_left_alone(builder):
    assert builder._fit_marker(DB2_CURSOR_FLAGS_MARKER) == (
        DB2_CURSOR_FLAGS_MARKER
    )
    assert not builder.messages


def test_an_unregistered_over_long_marker_is_truncated(builder):
    fitted = builder._fit_marker("X" * 200)

    assert len(fitted) <= COMMENT_TITLE_WIDTH
    assert fitted.endswith("...")


def test_an_empty_marker_yields_no_title(builder):
    assert builder._fit_marker("") == ""
    assert builder._fit_marker(None) == ""


# ---------------------------------------------------------------------
# Rendered line
# ---------------------------------------------------------------------
@pytest.mark.parametrize("marker", MARKERS_UNDER_TEST)
def test_every_marker_renders_as_one_line(builder, marker):
    """A wrapped banner is what produced the orphan '*FLAGS*' line."""
    assert len(builder._marker_lines(marker)) == 1


@pytest.mark.parametrize("marker", MARKERS_UNDER_TEST)
def test_every_marker_fits_the_body_window(builder, marker):
    for line in builder._marker_lines(marker):
        assert len(line) <= COMMENT_BODY_WIDTH


@pytest.mark.parametrize("marker", MARKERS_UNDER_TEST)
def test_every_marker_opens_and_closes_with_an_asterisk(builder, marker):
    line = builder._marker_lines(marker)[0]

    assert line.startswith("*")
    assert line.rstrip().endswith("*")


def test_an_empty_marker_emits_no_line(builder):
    assert builder._marker_lines("") == []
    assert builder._marker_lines(None) == []


# ---------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------
def test_the_short_form_fallback_is_reported(builder):
    """A silently shortened banner is a review problem."""
    builder._marker_lines(DB2_INFRASTRUCTURE_MARKER)

    assert any("short form" in note for note in builder.messages)


def test_truncation_is_reported(builder):
    builder._marker_lines("X" * 200)

    assert any("truncated" in note for note in builder.messages)