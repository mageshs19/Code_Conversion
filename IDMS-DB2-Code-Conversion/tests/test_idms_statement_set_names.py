# LOCATION: tests/test_idms_statement_set_names.py
# ACTION: CREATE NEW FILE

"""IDMS name rendering in generated *DB2: comments.

No import from another test module. `transform_line` is a fixture
supplied by tests/conftest.py.

CONTRACT
--------
An IDMS SET or RECORD name written into generated COBOL text must keep
its IDMS spelling (hyphens). NameNormalizer.normalize() produces a DB2
identifier and must never reach a comment.
"""


def test_set_name_keeps_idms_spelling_in_the_comment(transform_line):
    text, _opened = transform_line("OBTAIN FIRST VMB-FAR WITHIN AR-VMBFRM1.")

    assert "WITHIN AR-VMBFRM1" in text
    assert "AR_VMBFRM1" not in text


def test_record_name_keeps_cobol_spelling_in_the_comment(transform_line):
    text, _opened = transform_line("OBTAIN FIRST VMB-FAR WITHIN AR-VMBFRM1.")

    assert "OBTAIN FIRST VMB-FAR" in text
    assert "VMB_FAR" not in text


def test_obtain_next_keeps_idms_spelling(transform_line):
    text, _opened = transform_line("OBTAIN NEXT VMB-FAR WITHIN AR-VMBFRM1.")

    assert "OBTAIN NEXT VMB-FAR WITHIN AR-VMBFRM1" in text


def test_opened_set_is_still_the_normalized_key(transform_line):
    _text, opened = transform_line("OBTAIN FIRST VMB-FAR WITHIN AR-VMBFRM1.")

    assert opened == "AR_VMBFRM1"


def test_unmapped_record_never_emits_an_empty_cursor_perform(transform_line):
    text, opened = transform_line("OBTAIN FIRST NOSUCHREC WITHIN AR-VMBFRM1.")

    assert "PERFORM OPEN-." not in text
    assert "PERFORM FETCH-." not in text
    assert opened == ""


def test_find_first_without_a_record_is_kept_and_commented(transform_line):
    text, opened = transform_line("FIND FIRST WITHIN AR-VMBFRM1.")

    assert "PERFORM OPEN-." not in text
    assert opened == ""


def test_obtain_outside_procedure_division_is_only_commented(transform_line):
    text, opened = transform_line(
        "OBTAIN FIRST VMB-FAR WITHIN AR-VMBFRM1.",
        current_division="DATA",
    )

    assert "PERFORM" not in text
    assert opened == ""