"""Streamlit panel. Reviews whatever is currently in session state.

Reads only from session state and writes only to it. Imports nothing from
the converter, so the one-way dependency rule holds even here.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re

import streamlit as st

from code_review.engine.context import (
    KIND_RETRIEVAL,
    KIND_UPDATE,
    ReviewContext,
)
from code_review.engine.models import Outcome
from code_review.engine.reviewer import Reviewer, blockers, is_accepted
from code_review.report import csv_writer, text_writer
from code_review.standards import wording as w

IDMS_WRITE = re.compile(
    r"^\s*(?:\d{6}\s+)?(STORE|MODIFY|ERASE)\b", re.IGNORECASE | re.MULTILINE
)
STATE_KEY = "code_review_result"
STATE_STAMP = "code_review_stamp"
TEXT_ENCODING = "utf-8"


def _kind(source_text: str) -> str:
    """UPDATE when the source contains an IDMS write verb."""
    return (
        KIND_UPDATE
        if IDMS_WRITE.search(str(source_text or ""))
        else KIND_RETRIEVAL
    )


def _fingerprint() -> str:
    """Identity of the program currently held in session state.

    The converter resets its own generated-output keys when new inputs are
    loaded, but it knows nothing about the review result. Without this,
    a report produced for the retrieval program stays on screen after the
    update program is generated.
    """
    converted = str(st.session_state.get("converted_cobol", "") or "")
    digest = hashlib.sha1(
        converted.encode(TEXT_ENCODING, errors="replace")
    ).hexdigest()
    return "|".join([
        str(st.session_state.get("idms_cobol_source_name", "") or ""),
        str(st.session_state.get("converted_cobol_file_name", "") or ""),
        str(len(converted)),
        digest,
    ])


def build_context() -> ReviewContext:
    source = st.session_state.get("idms_cobol_text", "")
    return ReviewContext(
        program_name=(
            st.session_state.get("idms_cobol_source_name", "")
            or w.VALUE_UNNAMED
        ),
        program_kind=_kind(source),
        target_program_id="",
        source_file=st.session_state.get("converted_cobol_file_name", ""),
        converted_cobol=st.session_state.get("converted_cobol", ""),
        source_cobol=source,
        sheet_mapping_rows=st.session_state.get("sheet_mapping_rows", []),
        dclgen_columns=st.session_state.get("dclgen_columns", []),
        copybook_fields=st.session_state.get("copybook_fields", []),
    )


def render_review_panel() -> None:
    st.markdown(f"## {w.UI_TITLE}")

    if not st.session_state.get("converted_cobol"):
        _discard()
        st.info(w.UI_NOT_READY)
        return

    current = _fingerprint()
    result = _current_result(current)

    st.caption(w.UI_TARGET.format(
        file=st.session_state.get("converted_cobol_file_name", "")
        or w.VALUE_IN_MEMORY,
        kind=_kind(st.session_state.get("idms_cobol_text", "")),
    ))

    left, _right = st.columns([1, 3])
    with left:
        if st.button(w.UI_RUN, type="primary", key="code_review_run"):
            result = Reviewer().review(build_context())
            st.session_state[STATE_KEY] = result
            st.session_state[STATE_STAMP] = current

    if result is None:
        st.info(w.UI_RUN_HINT)
        st.caption(w.UI_SCOPE)
        return

    _render_verdict(result)
    _render_totals(result)
    _render_detail(result)
    _render_downloads(result)
    st.caption(w.UI_SCOPE)


# ---- state -----------------------------------------------------------
def _discard() -> None:
    st.session_state.pop(STATE_KEY, None)
    st.session_state.pop(STATE_STAMP, None)


def _current_result(current: str):
    """The stored report, but only when it belongs to this program."""
    result = st.session_state.get(STATE_KEY)
    if result is None:
        return None
    if st.session_state.get(STATE_STAMP) == current:
        return result
    _discard()
    st.warning(w.UI_STALE)
    return None


# ---- sections --------------------------------------------------------
def _render_verdict(result) -> None:
    st.markdown(w.UI_PROGRAM.format(
        name=result.program_name or w.VALUE_UNNAMED,
        kind=result.program_kind or w.VALUE_UNKNOWN,
        file=result.source_file or w.VALUE_IN_MEMORY,
    ))

    if is_accepted(result):
        st.success(w.UI_ACCEPTED)
    else:
        st.error(w.UI_REJECTED.format(
            ids=", ".join(c.check_id for c in blockers(result))
        ))


def _render_totals(result) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(w.UI_METRIC_PASSED, result.passed)
    c2.metric(w.UI_METRIC_FAILED, result.failed)
    c3.metric(w.UI_METRIC_SKIPPED, result.skipped)
    c4.metric(w.UI_METRIC_BLOCKED, result.blocked)

    st.caption(w.UI_CRITERIA.format(
        passed=result.criteria_passed,
        failed=result.criteria_failed,
        skipped=result.criteria_skipped,
        blocked=result.criteria_blocked,
    ))


def _render_detail(result) -> None:
    col_left, col_right = st.columns(2)
    with col_left:
        failures_only = st.checkbox(
            w.UI_FILTER_FAILURES, value=False, key="code_review_filter",
        )
    with col_right:
        show_skips = st.checkbox(
            w.UI_FILTER_SKIPS, value=True, key="code_review_skips",
        )

    for check in result.checks:
        if failures_only and check.outcome is not Outcome.FAIL:
            continue

        label = w.UI_CHECK_LABEL.format(
            outcome=check.outcome.value,
            check_id=check.check_id,
            severity=check.severity,
            title=check.title,
        )
        with st.expander(label, expanded=check.outcome is Outcome.FAIL):
            _render_criteria(check, show_skips)


def _render_criteria(check, show_skips: bool) -> None:
    for crit in check.criteria:
        if crit.outcome is Outcome.PASS:
            continue
        if crit.outcome is Outcome.SKIPPED and not show_skips:
            continue

        st.markdown(w.UI_CRITERION.format(
            mark=crit.outcome.value,
            criterion_id=crit.criterion_id,
            description=crit.description,
        ))
        if crit.note:
            st.caption(crit.note)
        if crit.findings:
            st.code(
                "\n".join(f.render() for f in crit.findings),
                language="text",
            )


def _render_downloads(result) -> None:
    st.markdown("---")
    stem = (result.program_name or w.UI_DEFAULT_STEM).replace(" ", "_")

    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            w.UI_DOWNLOAD_TEXT,
            data=text_writer.render(result),
            file_name=w.UI_FILE_TEXT.format(stem=stem),
            mime=w.UI_MIME_TEXT,
            key="code_review_download_text",
        )
    with d2:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(w.CSV_HEADER)
        writer.writerows(csv_writer.rows(result))
        st.download_button(
            w.UI_DOWNLOAD_CSV,
            data=buffer.getvalue(),
            file_name=w.UI_FILE_CSV.format(stem=stem),
            mime=w.UI_MIME_CSV,
            key="code_review_download_csv",
        )