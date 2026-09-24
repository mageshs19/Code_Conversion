# LOCATION: tests/test_db2_date_comparison.py
# ACTION: CREATE NEW FILE

"""DB2 DATE comparison conversion.

REGRESSION CONTRACT
-------------------
A DB2 DATE host is stored as DD.MM.CCYY (10 bytes). A COBOL date field is
CCYYMMDD, PIC 9(8). Comparing them directly compares '0' against '2' and
selects the wrong rows. Every DATE host that takes part in a comparison
must therefore be realigned into its HELP- helper first.

The two historical blockers, each fatal on its own:

  1. the host had to be the FIRST token after IF, so a parenthesised
     condition never matched,
  2. the condition had to contain the literal token PARMDATE, a hardcoded
     host variable belonging to one program.
"""

import pytest

from idms_db2_phase2.composers.db2_date_comparison_composer import (
    Db2DateComparisonComposer,
)
from idms_db2_phase2.composers.db2_date_condition_assembler import (
    Db2DateConditionAssembler,
)
from idms_db2_phase2.composers.db2_date_field_detector import (
    Db2DateFieldDetector,
)


#
# Fixtures
#
@pytest.fixture
def composer() -> Db2DateComparisonComposer:
    return Db2DateComparisonComposer()


@pytest.fixture
def detector() -> Db2DateFieldDetector:
    return Db2DateFieldDetector()


@pytest.fixture
def assembler() -> Db2DateConditionAssembler:
    return Db2DateConditionAssembler()


def _program(body: str) -> str:
    return (
        "       WORKING-STORAGE SECTION.\n"
        "       01  WS-A                      PIC X.\n"
        "       PROCEDURE DIVISION.\n"
        f"{body}"
    )


#
# The exact VMDZ7200 condition
#
VMDZ7200_CONDITION = (
    "           IF (DA-CPTAFS-479BFAS OF DCLDZBFASTV < DA-ARCH-YMD\n"
    "              AND DA-CPTAFS-479BFAS OF DCLDZBFASTV NOT = '00000000') OR\n"
    "              (DA-CRFMAS-479BFAS OF DCLDZBFASTV < DA-ARCH-YMD AND\n"
    "              DA-CPTAFS-479BFAS OF DCLDZBFASTV = '00000000')\n"
    "              ADD 1 TO WS-TELLER\n"
    "           END-IF.\n"
)


#
# Assembler
#
def test_assembler_joins_a_four_line_parenthesised_condition(assembler):
    lines = _program(VMDZ7200_CONDITION).splitlines()
    start = next(
        index
        for index, line in enumerate(lines)
        if line.strip().startswith("IF (")
    )

    span = assembler.span_at(lines, start)

    assert span is not None
    assert span.complete is True
    assert span.line_count == 4
    assert "DA-CPTAFS-479BFAS" in span.text
    assert "DA-CRFMAS-479BFAS" in span.text


def test_assembler_stops_before_the_statement_body(assembler):
    lines = _program(VMDZ7200_CONDITION).splitlines()
    start = next(
        index
        for index, line in enumerate(lines)
        if line.strip().startswith("IF (")
    )

    span = assembler.span_at(lines, start)

    assert "ADD 1 TO WS-TELLER" not in span.text


#
# Detector
#
def test_detector_finds_both_hosts_in_a_compound_condition(detector):
    lines = _program(VMDZ7200_CONDITION).splitlines()

    fields = detector.date_fields_used_in_comparisons(lines)

    assert "DA-CPTAFS-479BFAS" in fields
    assert "DA-CRFMAS-479BFAS" in fields


def test_detector_no_longer_requires_the_token_parmdate(detector):
    body = (
        "           IF DA-CPTAFS-479BFAS OF DCLDZBFASTV < DA-ARCH-YMD\n"
        "              CONTINUE\n"
        "           END-IF.\n"
    )
    lines = _program(body).splitlines()

    assert detector.date_fields_used_in_comparisons(lines) == [
        "DA-CPTAFS-479BFAS"
    ]


def test_detector_ignores_a_reference_with_no_comparison(detector):
    body = (
        "           IF WS-A = 'Y'\n"
        "              MOVE DA-CPTAFS-479BFAS OF DCLDZBFASTV TO WS-A\n"
        "           END-IF.\n"
    )
    lines = _program(body).splitlines()

    assert detector.date_fields_used_in_comparisons(lines) == []


def test_detector_never_touches_an_exec_sql_host(detector):
    body = (
        "           EXEC SQL\n"
        "             FETCH DZBFASC1\n"
        "             INTO :DCLDZBFASTV.DA-CPTAFS-479BFAS\n"
        "           END-EXEC.\n"
    )
    lines = _program(body).splitlines()

    assert detector.date_fields_used_in_comparisons(lines) == []


#
# Composer - end to end
#
def test_compound_condition_is_rewritten_onto_helpers(composer):
    output = composer.compose(_program(VMDZ7200_CONDITION))

    assert "HELP-DA-CPTAFS-479BFAS" in output
    assert "HELP-DA-CRFMAS-479BFAS" in output
    assert "DA-CPTAFS-479BFAS OF DCLDZBFASTV <" not in output


def test_realignment_block_is_emitted_before_the_if(composer):
    output = composer.compose(_program(VMDZ7200_CONDITION))
    lines = output.splitlines()

    realign = next(
        index for index, line in enumerate(lines) if "DA-DD-MM-CCYY" in line
    )
    condition = next(
        index for index, line in enumerate(lines) if line.strip().startswith("IF")
    )

    assert realign < condition


def test_shared_date_working_storage_is_declared(composer):
    output = composer.compose(_program(VMDZ7200_CONDITION))

    assert "DA-CCYYMMDD" in output
    assert "DA-DD-MM-CCYY" in output


def test_original_line_breaks_are_preserved(composer):
    """The four physical lines of the condition stay four lines.

    Bounded precisely between the IF and the first statement of the
    body. An earlier version of this test counted every line mentioning
    HELP-DA-, which also caught the two Working-Storage declarations the
    pass legitimately generates, and reported 6.
    """
    output = composer.compose(_program(VMDZ7200_CONDITION))
    lines = output.splitlines()

    start = next(
        index
        for index, line in enumerate(lines)
        if line.strip().startswith("IF ")
    )
    end = next(
        index
        for index, line in enumerate(lines)
        if "ADD 1 TO WS-TELLER" in line
    )

    condition_lines = [
        line for line in lines[start:end] if line.strip()
    ]

    assert len(condition_lines) == 4
    assert all("HELP-DA-" in line for line in condition_lines)


def test_one_helper_field_is_declared_per_converted_host(composer):
    """The realignment target must exist in Working-Storage."""
    output = composer.compose(_program(VMDZ7200_CONDITION))

    declarations = [
        line for line in output.splitlines()
        if "HELP-DA-" in line and "PIC" in line
    ]

    assert len(declarations) == 2
    assert any("HELP-DA-CPTAFS-479BFAS" in line for line in declarations)
    assert any("HELP-DA-CRFMAS-479BFAS" in line for line in declarations)

def test_literals_and_business_operands_are_untouched(composer):
    output = composer.compose(_program(VMDZ7200_CONDITION))

    assert "'00000000'" in output
    assert "DA-ARCH-YMD" in output
    assert "ADD 1 TO WS-TELLER" in output


#
# Diagnostics - the pass must never be silent
#
def test_conversion_is_reported(composer):
    composer.compose(_program(VMDZ7200_CONDITION))
    joined = " ".join(composer.messages)

    assert "DB2 date compare" in joined
    assert "realigned" in joined


def test_a_program_with_no_dates_says_so(composer):
    body = (
        "           IF WS-A = 'Y'\n"
        "              CONTINUE\n"
        "           END-IF.\n"
    )

    composer.compose(_program(body))

    assert any(
        "no DB2 DATE host is compared" in message
        for message in composer.messages
    )


def test_empty_text_is_safe(composer):
    assert composer.compose("") == ""
    assert composer.messages == []

#
# Fixed-format geometry
#
def _fixed(seq: str, body: str, right: str) -> str:
    """An 80-column line: 6 seq, 1 indicator, 65 body, 8 right seq."""
    return f"{seq} {body[:65].ljust(65)}{right}"


FIXED_CONDITION = [
    _fixed("002110", "     IF (DA-CPTAFS-479BFAS OF DCLDZBFASTV < DA-ARCH-YMD", "02110000"),
    _fixed("002120", "        AND DA-CPTAFS-479BFAS OF DCLDZBFASTV NOT = '00000000') OR", "02120000"),
    _fixed("002130", "        (DA-CRFMAS-479BFAS OF DCLDZBFASTV < DA-ARCH-YMD AND", "02130000"),
    _fixed("002140", "        DA-CPTAFS-479BFAS OF DCLDZBFASTV = '00000000')", "02140000"),
    _fixed("002150", "        ADD 1 TO WS-TELLER", "02150000"),
    _fixed("002160", "     END-IF.", "02160000"),
]


def test_substitution_keeps_every_line_at_eighty_columns():
    """The right sequence area must stay at column 73.

    Substituting into the raw line shortened it by 10 characters, slid
    the sequence number to column 63, and the indent normalizer then
    wrapped the corrupted body onto two lines.
    """
    from idms_db2_phase2.composers.db2_date_comparison_rewriter import (
        Db2DateComparisonRewriter,
    )

    header = [
        _fixed("001750", " PROCEDURE DIVISION.", "01750000"),
        _fixed("002290", " BEHANDELING.", "02290000"),
    ]
    output = Db2DateComparisonRewriter().rewrite_date_comparisons(
        header + FIXED_CONDITION
    )

    rewritten = [line for line in output if "HELP-DA-" in line and "MOVE" not in line]

    assert rewritten, "no condition line was rewritten"

    for line in rewritten:
        assert len(line) == 80, f"geometry broken: {line!r}"
        assert line[:6].isdigit(), f"left sequence lost: {line!r}"
        assert line[72:80].isdigit(), f"right sequence moved: {line!r}"


def test_a_four_line_condition_stays_four_lines_when_fixed_format():
    from idms_db2_phase2.composers.db2_date_comparison_rewriter import (
        Db2DateComparisonRewriter,
    )

    header = [
        _fixed("001750", " PROCEDURE DIVISION.", "01750000"),
        _fixed("002290", " BEHANDELING.", "02290000"),
    ]
    output = Db2DateComparisonRewriter().rewrite_date_comparisons(
        header + FIXED_CONDITION
    )

    rewritten = [line for line in output if "HELP-DA-" in line and "MOVE" not in line]

    assert len(rewritten) == 4

#
# Fixed-format geometry
#
def _fixed(seq: str, body: str, right: str) -> str:
    """An exact 80-column record: 6 seq + 1 indicator + 65 body + 8 seq."""
    assert len(body) <= 65
    return f"{seq} {body.ljust(65)}{right}"


FIXED_PROGRAM = [
    _fixed("001750", " PROCEDURE DIVISION.", "01750000"),
    _fixed("002290", " BEHANDELING.", "02290000"),
    _fixed("002110", "     IF (DA-CPTAFS-479BFAS OF DCLDZBFASTV < DA-ARCH-YMD", "02110000"),
    _fixed("002120", "        AND DA-CPTAFS-479BFAS OF DCLDZBFASTV NOT = '00000000') OR", "02120000"),
    _fixed("002130", "        (DA-CRFMAS-479BFAS OF DCLDZBFASTV < DA-ARCH-YMD AND", "02130000"),
    _fixed("002140", "        DA-CPTAFS-479BFAS OF DCLDZBFASTV = '00000000')", "02140000"),
    _fixed("002150", "        ADD 1 TO WS-TELLER", "02150000"),
    _fixed("002160", "     END-IF.", "02160000"),
]


def _rewrite_fixed():
    from idms_db2_phase2.composers.db2_date_comparison_rewriter import (
        Db2DateComparisonRewriter,
    )

    output = Db2DateComparisonRewriter().rewrite_date_comparisons(
        list(FIXED_PROGRAM)
    )
    return [line for line in output if "HELP-DA-" in line and "MOVE" not in line]


def test_every_rewritten_record_is_exactly_eighty_columns():
    for line in _rewrite_fixed():
        assert len(line) == 80, f"geometry broken: {line!r}"
        assert line[0:6].isdigit(), f"left sequence lost: {line!r}"
        assert line[72:80].isdigit(), f"right sequence moved: {line!r}"


def test_a_four_line_condition_stays_four_lines():
    assert len(_rewrite_fixed()) == 4


def test_no_stray_token_is_appended_to_the_body():
    """A wrapped pseudo-body once split the right sequence off as '0'."""
    for line in _rewrite_fixed():
        body = line[7:72].rstrip()
        assert not body.endswith(" 0"), f"stray token: {line!r}"
        assert "') 0" not in body, f"stray token: {line!r}"
        assert not body.endswith("AND 0"), f"stray token: {line!r}"


def test_the_condition_text_is_intact():
    bodies = [line[7:72].rstrip() for line in _rewrite_fixed()]
    joined = " ".join(bodies)

    assert "HELP-DA-CPTAFS-479BFAS < DA-ARCH-YMD" in joined
    assert "HELP-DA-CPTAFS-479BFAS NOT = '00000000'" in joined
    assert "HELP-DA-CRFMAS-479BFAS < DA-ARCH-YMD" in joined
    assert "OF DCLDZBFASTV" not in joined