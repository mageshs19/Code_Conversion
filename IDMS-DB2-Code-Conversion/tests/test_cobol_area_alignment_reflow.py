# LOCATION: tests/test_cobol_area_alignment_reflow.py
# ACTION: CREATE NEW FILE

from idms_db2_phase2.services.cobol_area_alignment_classifier import (
    CobolAreaAlignmentClassifier,
)
from idms_db2_phase2.services.cobol_area_alignment_reflow import (
    CobolAreaAlignmentReflow,
)
from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)


def _fixed(body: str, seq: str = "002770", right: str = "02770000") -> str:
    return f"{seq} {body[:65].ljust(65)}{right}"


def _reflow() -> CobolAreaAlignmentReflow:
    return CobolAreaAlignmentReflow(
        fixed_format=FixedFormatLineService(),
        classifier=CobolAreaAlignmentClassifier(),
    )


def _body(line: str) -> str:
    return line[7:72].rstrip()


def test_two_line_move_keeps_both_lines_and_full_name():
    first = _fixed("       MOVE AM-CNSTK-479BEFF OF DCLDZBEFFTV")
    second = _fixed("       TO UIT-AM-CN-STOCK", seq="002780", right="02780000")

    out = _reflow().try_reflow_with_next_line(
        current_line=first,
        next_line=second,
        first_indent="       ",
    )

    assert len(out) == 2
    assert "UIT-AM-CN-STOCK" in _body(out[1])
    assert "MOVE AM-CNSTK-479BEFF OF DCLDZBEFFTV" in _body(out[0])


def test_continuation_is_indented_one_level_further():
    first = _fixed("    MOVE A OF B")
    second = _fixed("    TO C", seq="002780", right="02780000")

    out = _reflow().try_reflow_with_next_line(
        current_line=first,
        next_line=second,
        first_indent="    ",
    )

    assert _body(out[0]).startswith("    MOVE")
    assert _body(out[1]).startswith("        TO")


def test_never_truncates_a_data_name():
    long_target = "TO UIT-SOME-VERY-LONG-OUTPUT-FIELD-NAME-HERE"
    first = _fixed("    MOVE SOURCE-FIELD-NAME OF DCLDZBEFFTV")
    second = _fixed(f"    {long_target}", seq="002780", right="02780000")

    out = _reflow().try_reflow_with_next_line(
        current_line=first,
        next_line=second,
        first_indent="    ",
    )

    combined = " ".join(_body(line) for line in out) if out else ""
    assert out == [] or "UIT-SOME-VERY-LONG-OUTPUT-FIELD-NAME-HERE" in combined


def test_next_paragraph_header_is_never_joined():
    first = _fixed("    MOVE A TO B")
    second = _fixed("VERWERK-VMBEVEF.", seq="002780", right="02780000")

    out = _reflow().try_reflow_with_next_line(
        current_line=first,
        next_line=second,
        first_indent="    ",
    )

    assert out == []


def test_next_statement_is_never_joined():
    first = _fixed("    MOVE A TO B")
    second = _fixed("    PERFORM 710-OPEN-DZBEFFC1", seq="002780",
                    right="02780000")

    out = _reflow().try_reflow_with_next_line(
        current_line=first,
        next_line=second,
        first_indent="    ",
    )

    assert out == []


def test_statement_is_not_collapsed_onto_one_line():
    first = _fixed("    MOVE A OF B")
    second = _fixed("    TO C", seq="002780", right="02780000")

    out = _reflow().try_reflow_with_next_line(
        current_line=first,
        next_line=second,
        first_indent="    ",
    )

    assert len(out) == 2
    assert _body(out[1]).strip() != ""