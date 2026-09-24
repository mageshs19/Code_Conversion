# LOCATION: tests/test_record_picture_sizer.py
# ACTION: CREATE NEW FILE

"""PICTURE sizing.

REGRESSION
----------
    05  F-FORM                PIC X(478).

was measured at 1 byte because only the symbol 'X' was read. The length
guard then refused a 432-byte VMBFAS layout as "longer than the 1 byte
F-FORM declares", discarding roughly 400 lines of generated output.
"""

import pytest

from idms_db2_phase2.composers.record_materialisation.record_picture_sizer import (
    RecordPictureSizer,
)


@pytest.mark.parametrize(
    "body, expected",
    [
        ("05  F-FORM                PIC X(478).", 478),
        ("05  F-NR-IS               PIC 9(7).", 7),
        ("05  F-SW-ARCH             PIC X.", 1),
        ("01  DAARCH-REC            PIC X(20).", 20),
        ("05  W-NR-ID-ISSUE         PIC 9(7).", 7),
        ("03  D-YEAR                PIC 9(2).", 2),
        ("05  CCYY                  PIC 9999.", 4),
        ("05  F-TELLER              PIC S9(11) COMP-3.", 6),
    ],
)
def test_declared_bytes_reads_the_full_clause(body, expected):
    assert RecordPictureSizer.declared_bytes(body) == expected


def test_a_truncated_caller_capture_cannot_win():
    """The caller's group says 'X'; the line says 'X(478)'."""

    class _Match:
        def group(self, name):
            return "X"

    body = "05  F-FORM                PIC X(478)."

    assert RecordPictureSizer.declared_bytes(body, _Match()) == 478


def test_the_data_name_is_never_measured():
    """F-TARGET contains an A, which the symbol class matches."""
    assert RecordPictureSizer.declared_bytes(
        "05  F-TARGET              PIC X(20)."
    ) == 20


def test_comp_3_is_halved():
    assert RecordPictureSizer.size_of("S9(11)", "COMP-3") == 6
    assert RecordPictureSizer.size_of("9(7)", "COMP-3") == 4


def test_empty_and_unreadable_are_zero():
    assert RecordPictureSizer.declared_bytes("") == 0
    assert RecordPictureSizer.declared_bytes("05  F-GROUP.") == 0
    assert RecordPictureSizer.size_of("") == 0

def test_repeat_counts_are_honoured():
    """The defect: (n) was ignored and every clause measured 1."""
    assert RecordPictureSizer.size_of("X(478)") == 478
    assert RecordPictureSizer.size_of("9(7)") == 7
    assert RecordPictureSizer.size_of("9999") == 4
    assert RecordPictureSizer.size_of("XXX") == 3
    assert RecordPictureSizer.size_of("S9(13)V99") == 15


def test_whitespace_inside_the_repeat_is_tolerated():
    """The mapping workbook contains 'PIC X(4 )'."""
    assert RecordPictureSizer.declared_bytes("05  A-FIELD  PIC X(4 ).") == 4


def test_a_value_clause_is_not_measured():
    assert RecordPictureSizer.declared_bytes(
        "77  USERABEN  PIC X(8)   VALUE 'USERABEN'."
    ) == 8