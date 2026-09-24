# LOCATION: tests/test_condition_is_never_truncated.py
# ACTION: CREATE NEW FILE

"""No pass may lose characters from a PROCEDURE DIVISION statement.

REGRESSION
----------
A four-line IF condition was emitted as two lines truncated mid-name:

    IF (HELP-DA-CPTAFS-479BFAS < DA-ARCH-YMD  AND HELP-DA-CPTAFS-
       (HELP-DA-CRFMAS-479BFAS < DA-ARCH-YMD AND HELP-DA-CPTAFS-4

losing "NOT = '00000000') OR" and "= '00000000')" entirely.
"""

from idms_db2_phase2.composers.procedure_indent_normalizer import (
    ProcedureIndentNormalizer,
)

QUOTE = chr(39)
ZERO8 = QUOTE + "00000000" + QUOTE


def fixed(seq: str, body: str, right: str) -> str:
    assert len(body) <= 65
    return seq + " " + body.ljust(65) + right


SOURCE = "\n".join(
    [
        fixed("001410", " PROCEDURE DIVISION.", "01410000"),
        fixed("001990", " BEHANDELING.", "01990000"),
        fixed("002010", "     IF (HELP-DA-CPTAFS-479BFAS < DA-ARCH-YMD AND", "02010000"),
        fixed("002020", "        HELP-DA-CPTAFS-479BFAS NOT = " + ZERO8 + ") OR", "02020000"),
        fixed("002021", "        (HELP-DA-CRFMAS-479BFAS < DA-ARCH-YMD AND", "02021000"),
        fixed("002022", "        HELP-DA-CPTAFS-479BFAS = " + ZERO8 + ")", "02022000"),
        fixed("002030", "        ADD 1 TO WS-TELLER", "02030000"),
        fixed("002110", "     END-IF.", "02110000"),
    ]
) + "\n"


def _tokens(text: str) -> str:
    """Every non-blank character of every body, order preserved."""
    out = []

    for line in text.splitlines():
        body = line[7:72] if len(line) >= 72 else line
        out.append("".join(body.split()))

    return "".join(out)


def test_no_character_is_lost():
    result = ProcedureIndentNormalizer().compose(SOURCE)

    assert _tokens(result) == _tokens(SOURCE)


def test_no_identifier_is_cut_in_half():
    result = ProcedureIndentNormalizer().compose(SOURCE)

    assert "HELP-DA-CPTAFS-479BFAS" in result
    assert result.count("HELP-DA-CPTAFS-479BFAS") == 3
    assert ZERO8 in result


def test_every_record_stays_eighty_columns():
    result = ProcedureIndentNormalizer().compose(SOURCE)

    for line in result.splitlines():
        if line[:6].isdigit():
            assert len(line) == 80, f"geometry broken: {line!r}"