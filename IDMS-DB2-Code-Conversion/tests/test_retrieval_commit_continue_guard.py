# LOCATION: tests/test_retrieval_commit_continue_guard.py
# ACTION: REPLACE ENTIRE FILE
"""The COMMIT removal must never empty a paragraph.

The replacement is a COMMENT, which is not executable. A paragraph whose
only statement was the COMMIT block would be left with nothing the
compiler accepts.

FIXED-FORMAT NOTE - the helper below builds a FULL 80-column record:

    columns  1-6   left sequence
    column   7     indicator
    columns  8-72  body (65)
    columns 73-80  right sequence

A short line is not merely cosmetic here: strip_sequence_numbers() stops
recognising the right sequence, the trailing digits stay glued to the
logical line, and a paragraph header reads as a statement.
"""

from __future__ import annotations

from idms_db2_phase2.composers.retrieval_commit_cleanup_composer import (
    RetrievalCommitCleanupComposer,
)

LEFT_WIDTH = 6
BODY_WIDTH = 65
RIGHT_WIDTH = 8
LINE_WIDTH = 80


def _fixed(seq: str, body: str, indicator: str = " ") -> str:
    """One 80-column fixed-format record."""
    left = str(seq).zfill(LEFT_WIDTH)[:LEFT_WIDTH]
    right = f"{left}00"[:RIGHT_WIDTH].ljust(RIGHT_WIDTH, "0")
    line = f"{left}{indicator[:1]}{body[:BODY_WIDTH].ljust(BODY_WIDTH)}{right}"
    assert len(line) == LINE_WIDTH
    return line


def _paragraph(seq: str, name: str) -> str:
    return _fixed(seq, name)


def _statement(seq: str, body: str) -> str:
    return _fixed(seq, f"    {body}")


def _comment(seq: str, body: str) -> str:
    return _fixed(seq, body, indicator="*")


def _commit_block(start: int) -> list[str]:
    return [
        _statement(f"{start:06d}", "MOVE 'COMMIT' TO SQL-LOCATION."),
        _statement(f"{start + 10:06d}", "EXEC SQL"),
        _statement(f"{start + 20:06d}", "  COMMIT"),
        _statement(f"{start + 30:06d}", "END-EXEC."),
    ]


def _compose(lines: list[str]) -> tuple[str, list[str]]:
    composer = RetrievalCommitCleanupComposer(is_update_program=False)
    return composer.compose("\n".join(lines)), composer.messages


# =====================================================================
# The guard fires
# =====================================================================
def test_continue_is_added_when_the_paragraph_is_emptied():
    result, messages = _compose(
        [
            _paragraph("007410", "EINDE-PROGRAMMA."),
            *_commit_block(7430),
            _paragraph("007470", "EINDE-PROGRAMMA-EXIT."),
        ]
    )

    assert "CONTINUE." in result
    assert any("only statement in its paragraph" in m for m in messages)


def test_a_following_comment_does_not_rescue_the_paragraph():
    """A comment is not executable."""
    result, _messages = _compose(
        [
            _paragraph("007410", "EINDE-PROGRAMMA."),
            *_commit_block(7430),
            _comment("007470", "A NOTE"),
            _paragraph("007480", "EINDE-PROGRAMMA-EXIT."),
        ]
    )

    assert "CONTINUE." in result


def test_end_of_program_after_the_removal_adds_continue():
    result, _messages = _compose(
        [
            _paragraph("007410", "EINDE-PROGRAMMA."),
            *_commit_block(7430),
        ]
    )

    assert "CONTINUE." in result


def test_a_following_section_header_is_a_boundary():
    result, _messages = _compose(
        [
            _paragraph("007410", "EINDE-PROGRAMMA."),
            *_commit_block(7430),
            _fixed("007470", "WORKING-STORAGE SECTION."),
        ]
    )

    assert "CONTINUE." in result


# =====================================================================
# The guard stands down
# =====================================================================
def test_continue_is_not_added_when_a_statement_follows():
    result, messages = _compose(
        [
            _paragraph("007410", "EINDE-PROGRAMMA."),
            *_commit_block(7430),
            _statement("007470", "CLOSE FORM."),
        ]
    )

    assert "CONTINUE." not in result
    assert not any("only statement" in m for m in messages)


def test_exit_does_not_count_as_a_paragraph_boundary():
    """EXIT. belongs to the paragraph, so the paragraph is NOT empty."""
    result, _messages = _compose(
        [
            _paragraph("007410", "EINDE-PROGRAMMA."),
            *_commit_block(7430),
            _statement("007470", "EXIT."),
        ]
    )

    assert "CONTINUE." not in result


def test_goback_does_not_count_as_a_paragraph_boundary():
    result, _messages = _compose(
        [
            _paragraph("007410", "EINDE-PROGRAMMA."),
            *_commit_block(7430),
            _statement("007470", "GOBACK."),
        ]
    )

    assert "CONTINUE." not in result


# =====================================================================
# Geometry and scope
# =====================================================================
def test_the_generated_pair_keeps_the_sequence_area():
    result, _messages = _compose(
        [
            _paragraph("007410", "EINDE-PROGRAMMA."),
            *_commit_block(7430),
            _paragraph("007470", "EINDE-PROGRAMMA-EXIT."),
        ]
    )

    generated = [
        line
        for line in result.split("\n")
        if "CONTINUE." in line or "COMMIT removed" in line
    ]

    assert generated
    for line in generated:
        assert line[:LEFT_WIDTH].isdigit()
        assert len(line) == LINE_WIDTH


def test_continue_lands_in_area_b():
    """CONTINUE. must start at column 12, not Area A."""
    result, _messages = _compose(
        [
            _paragraph("007410", "EINDE-PROGRAMMA."),
            *_commit_block(7430),
            _paragraph("007470", "EINDE-PROGRAMMA-EXIT."),
        ]
    )

    line = next(l for l in result.split("\n") if "CONTINUE." in l)

    assert line.index("CONTINUE.") >= 11


def test_an_update_program_is_untouched():
    source = "\n".join(
        [
            _paragraph("007410", "EINDE-PROGRAMMA."),
            *_commit_block(7430),
        ]
    )
    composer = RetrievalCommitCleanupComposer(is_update_program=True)

    assert composer.compose(source) == source
    assert any("COMMIT kept" in m for m in composer.messages)


def test_empty_text_is_safe():
    assert RetrievalCommitCleanupComposer().compose("") == ""