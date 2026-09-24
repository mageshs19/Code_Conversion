# LOCATION: tests/test_field_reference_geometry.py
# ACTION: CREATE NEW FILE

"""Fixed-format geometry of the qualified field rewrite.

REGRESSION
----------
    002020         DA-CPTA-FORM-AS OF VMBFAS NOT = '00000000') OR           00002020

is 80 columns. The rewrite makes the text 7 characters longer, so
substituting into the WHOLE record produced 87 characters and pushed
00002020 from column 73 to column 80. Later passes read the first
displaced digit as body text and emitted

    AND HELP-DA-CPTAFS-479BFAS NOT = '00000000') OR 0
"""

import pytest

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from idms_db2_phase2.transformers.field_reference_rewriter import (
    FieldReferenceRewriter,
)

QUOTE = chr(39)
ZERO8 = QUOTE + "00000000" + QUOTE


def fixed(seq: str, body: str, right: str) -> str:
    assert len(body) <= 65
    return seq + " " + body.ljust(65) + right


SOURCE = "\n".join(
    [
        fixed("001410", " PROCEDURE DIVISION.", "00001410"),
        fixed("001990", " BEHANDELING.", "00001990"),
        fixed("002010", "     IF (DA-CPTA-FORM-AS OF VMBFAS < DA-ARCH-YMD AND", "00002010"),
        fixed("002020", "        DA-CPTA-FORM-AS OF VMBFAS NOT = " + ZERO8 + ") OR", "00002020"),
        fixed("002030", "        ADD 1 TO WS-TELLER", "00002030"),
        fixed("002110", "     END-IF.", "00002110"),
    ]
) + "\n"


@pytest.fixture
def rewriter(transformer_context):
    """Reuses the shared repositories from tests/conftest.py."""
    return FieldReferenceRewriter(
        mapping_repository=transformer_context["mapping_repository"],
        table_name_resolver=transformer_context["table_resolver"],
        host_variable_resolver=transformer_context["host_resolver"],
    )


def test_every_emitted_record_keeps_its_geometry(rewriter):
    output = rewriter.rewrite(SOURCE)

    for line in output.splitlines():
        if not line.strip():
            continue
        if not line[:6].isdigit():
            continue

        assert len(line) == 80, f"geometry broken: {line!r}"
        assert line[72:80].isdigit(), f"right sequence moved: {line!r}"


def test_no_stray_sequence_digit_leaks_into_the_body(rewriter):
    output = rewriter.rewrite(SOURCE)

    for line in output.splitlines():
        body = line[7:72].rstrip() if len(line) >= 72 else line
        assert not body.endswith(" 0"), f"stray digit: {line!r}"


def test_trailing_blanks_are_preserved(rewriter):
    """Blanks in columns 8-72 position the right sequence at column 73."""
    output = rewriter.rewrite(SOURCE)
    lines = [line for line in output.splitlines() if line[:6].isdigit()]

    assert lines
    assert all(len(line) == 80 for line in lines)


def test_a_line_with_no_reference_is_untouched(rewriter):
    output = rewriter.rewrite(SOURCE)

    assert any(
        "ADD 1 TO WS-TELLER" in line for line in output.splitlines()
    )