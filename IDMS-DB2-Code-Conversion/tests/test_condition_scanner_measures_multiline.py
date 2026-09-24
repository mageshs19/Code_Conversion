# LOCATION: tests/test_condition_scanner_measures_multiline.py
# ACTION: CREATE NEW FILE
"""A dangling boolean operator must never close a condition.

REGRESSION
----------
condition_end_index() inspected only the NEXT line's first word, so

    IF (HELP-DA-CPTAFS-479BFAS < DA-ARCH-YMD  AND
    HELP-DA-CPTAFS-479BFAS NOT = '00000000') OR
    (HELP-DA-CRFMAS-479BFAS < DA-ARCH-YMD AND
    HELP-DA-CPTAFS-479BFAS = '00000000')

measured as ONE line. OutputWriteGuard then allowed an extraction that
cut the IF away from its own condition tail:

    IF (HELP-DA-CPTAFS-479BFAS < DA-ARCH-YMD  AND
       PERFORM WRITE-FORM-REC
    END-IF.
    ...
    WRITE-FORM-REC.
       HELP-DA-CPTAFS-479BFAS NOT = '00000000') OR
"""

import pytest

from idms_db2_phase2.composers.output_write.output_write_guard import (
    OutputWriteGuard,
)
from idms_db2_phase2.services.cobol_condition_scanner import (
    CobolConditionScanner,
)

QUOTE = chr(39)
ZERO8 = QUOTE + "00000000" + QUOTE


def fixed(seq: str, body: str, right: str) -> str:
    assert len(body) <= 65
    return seq + " " + body.ljust(65) + right


HEADER = [
    fixed("001750", " PROCEDURE DIVISION.", "01750000"),
    fixed("002290", " BEHANDELING.", "02290000"),
]

FOUR_LINE = [
    fixed("002600", "    IF (HELP-DA-CPTAFS-479BFAS < DA-ARCH-YMD  AND", "02600000"),
    fixed("002610", "    HELP-DA-CPTAFS-479BFAS NOT = " + ZERO8 + ") OR", "02610000"),
    fixed("002620", "    (HELP-DA-CRFMAS-479BFAS < DA-ARCH-YMD AND", "02620000"),
    fixed("002630", "    HELP-DA-CPTAFS-479BFAS = " + ZERO8 + ")", "02630000"),
    fixed("002660", "       ADD 1 TO WS-TELLER", "02660000"),
    fixed("002770", "    END-IF.", "02770000"),
]


@pytest.fixture
def scanner():
    return CobolConditionScanner()


def test_a_four_line_condition_measures_four(scanner):
    lines = HEADER + FOUR_LINE
    if_index = len(HEADER)

    assert scanner.condition_line_count(lines, if_index) == 4


def test_a_line_ending_on_and_never_closes_the_condition(scanner):
    """The defect in one assertion."""
    lines = HEADER + FOUR_LINE
    if_index = len(HEADER)

    assert scanner.condition_end_index(lines, if_index) > if_index


def test_a_single_line_condition_still_measures_one(scanner):
    """The fix must not make every condition look multi-line."""
    lines = HEADER + [
        fixed("002600", "    IF WS-FLAG = " + QUOTE + "Y" + QUOTE, "02600000"),
        fixed("002610", "       ADD 1 TO WS-TELLER", "02610000"),
        fixed("002620", "    END-IF.", "02620000"),
    ]

    assert scanner.condition_line_count(lines, len(HEADER)) == 1


def test_the_guard_refuses_extraction_for_this_program():
    """The end-to-end contract OutputWriteGuard exists to enforce."""
    text = "\n".join(HEADER + FOUR_LINE) + "\n"

    assert OutputWriteGuard().blocks_extraction(text) is True


def test_the_guard_allows_extraction_for_a_single_line_condition():
    text = "\n".join(
        HEADER
        + [
            fixed("002600", "    IF WS-FLAG = " + QUOTE + "Y" + QUOTE, "02600000"),
            fixed("002610", "       WRITE FORM-REC FROM REC-FORM", "02610000"),
            fixed("002620", "    END-IF.", "02620000"),
        ]
    ) + "\n"

    assert OutputWriteGuard().blocks_extraction(text) is False