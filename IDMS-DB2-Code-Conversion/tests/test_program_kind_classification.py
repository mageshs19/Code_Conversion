# LOCATION: tests/test_program_kind_classification.py
# ACTION: CREATE NEW FILE
"""Program kind must be readable from FIXED-FORMAT source.

REGRESSION - the classifier anchored on "^\\s*STORE", which cannot match
a line whose columns 1-6 hold a sequence number. Every program was
classified RETRIEVAL, so an update program would lose its COMMIT.
"""

from __future__ import annotations

from patterns.idms_patterns import IDMS_WRITE_VERB_PATTERN


def _fixed(seq: str, body: str) -> str:
    return f"{seq} {body[:65].ljust(65)} {seq}0"


def test_a_sequenced_store_line_is_recognised():
    assert IDMS_WRITE_VERB_PATTERN.search(_fixed("002220", "STORE VMBFAS."))


def test_a_sequenced_modify_line_is_recognised():
    assert IDMS_WRITE_VERB_PATTERN.search(_fixed("002230", "MODIFY VMBFAS."))


def test_a_sequenced_erase_line_is_recognised():
    assert IDMS_WRITE_VERB_PATTERN.search(_fixed("002240", "ERASE VMBFAS."))


def test_a_retrieval_program_is_not_matched():
    source = "\n".join(
        [
            _fixed("001920", "OBTAIN FIRST VMBTL03-R01 WHERE SWEEP-VMBFAS."),
            _fixed("002220", "FINISH."),
            _fixed("002230", "CLOSE FORM."),
        ]
    )
    assert not IDMS_WRITE_VERB_PATTERN.search(source)


def test_the_word_must_be_a_verb_not_a_substring():
    """RESTORE-COUNT must not classify a program as UPDATE."""
    assert not IDMS_WRITE_VERB_PATTERN.search(
        _fixed("001000", "MOVE RESTORE-COUNT TO WS-X.")
    )