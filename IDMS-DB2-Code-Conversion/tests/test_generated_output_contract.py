# LOCATION: tests/test_generated_output_contract.py
# ACTION: CREATE NEW FILE

"""Asserts the three fixes against the ACTUAL generated .cbl.

Unit tests prove the builders are right. This proves the builders are
the ones reaching the output - the failure mode that cost several runs
when an unwired generator produced a parallel, unused implementation.

Skips when nothing has been generated yet, so a clean checkout still
passes.
"""

from __future__ import annotations

import re

import pytest

from config.path_settings import DEFAULT_RETRIEVAL_OUTPUT_DIR

COBOL_GLOB = "*.cbl"


@pytest.fixture(scope="module")
def generated_bodies() -> list[str]:
    folder = DEFAULT_RETRIEVAL_OUTPUT_DIR

    if not folder.exists():
        pytest.skip(f"No output folder yet: {folder}")

    files = sorted(
        (path for path in folder.glob(COBOL_GLOB) if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not files:
        pytest.skip(f"No generated .cbl in {folder}")

    text = files[0].read_text(encoding="utf-8", errors="replace")

    # Columns 8-72 only: sequence areas are not under test.
    return [
        line[7:72].strip()
        for line in text.splitlines()
        if line[7:72].strip()
    ]


def test_every_fetch_paragraph_initializes_its_host_group(generated_bodies):
    fetches = [
        index
        for index, body in enumerate(generated_bodies)
        if re.match(r"^\d{3,6}-FETCH-[A-Z0-9-]+\.$", body)
    ]

    assert fetches, "no generated FETCH paragraph found"

    for index in fetches:
        window = generated_bodies[index : index + 4]
        assert any(b.startswith("INITIALIZE DCL") for b in window), window


def test_every_error_branch_sets_sql_location(generated_bodies):
    """Only EVALUATE SQLCODE error branches must set SQL-LOCATION.

    EVALUATE TRUE date-realignment blocks also carry a WHEN OTHER whose
    first statement is MOVE CCYY OF DA-DD-MM-CCYY TO CCYY OF
    DA-CCYYMMDD-R. That branch is not an SQL error branch and must not
    be measured by this contract.
    """
    in_sqlcode_evaluate = False
    checked = 0

    for index, body in enumerate(generated_bodies):
        text = body.strip().upper()

        if text.startswith("EVALUATE SQLCODE"):
            in_sqlcode_evaluate = True
            continue

        if text.startswith("EVALUATE"):
            in_sqlcode_evaluate = False
            continue

        if text.startswith("END-EVALUATE"):
            in_sqlcode_evaluate = False
            continue

        if not in_sqlcode_evaluate:
            continue

        if text != "WHEN OTHER":
            continue

        assert generated_bodies[index + 1].strip().endswith("TO SQL-LOCATION"), (
            f"SQLCODE error branch at body index {index} does not set "
            f"SQL-LOCATION: {generated_bodies[index + 1]!r}"
        )
        checked += 1

    assert checked > 0, "No EVALUATE SQLCODE error branch was found to verify."

def test_every_declare_carries_a_queryno(generated_bodies):
    declares = [b for b in generated_bodies if b.startswith("DECLARE ")]
    querynos = [b for b in generated_bodies if b.startswith("QUERYNO ")]

    assert declares, "no DECLARE CURSOR found"
    assert len(querynos) == len(declares)


def test_no_empty_initialize_statement(generated_bodies):
    assert "INITIALIZE ." not in generated_bodies