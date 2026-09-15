# LOCATION: src/idms_db2_phase2/ui/test_panel.py
# ACTION: CREATE NEW FILE

"""Streamlit panel for running the Python test suite.

Reads only from session state and writes only to it. Contains no test
logic of its own: discovery, invocation and report parsing all live in
idms_db2_phase2.testing.pytest_runner, so the panel stays
presentation-only and the runner stays testable.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime

import streamlit as st

from idms_db2_phase2.testing.pytest_runner import (
    PytestRunner,
    TestRunResult,
)
from rules.test_runner_rules import (
    ALL_TESTS_LABEL,
    COLUMN_DURATION,
    COLUMN_MESSAGE,
    COLUMN_MODULE,
    COLUMN_OUTCOME,
    COLUMN_TEST,
    FILE_TIMESTAMP_FORMAT,
    MESSAGE_PREVIEW_LENGTH,
    OUTCOME_ICONS,
    RUN_TIMEOUT_SECONDS,
    TABLE_COLUMNS,
    UI_ALL_PASSED,
    UI_COMMAND_HEADER,
    UI_DETAIL_HEADER,
    UI_DOWNLOAD_CSV,
    UI_DOWNLOAD_LOG,
    UI_FAILURES_ONLY_LABEL,
    UI_FILE_CSV,
    UI_FILE_LOG,
    UI_HEADER,
    UI_INTRO,
    UI_KEYWORD_LABEL,
    UI_KEYWORD_PLACEHOLDER,
    UI_METRIC_DURATION,
    UI_METRIC_FAILED,
    UI_METRIC_PASSED,
    UI_METRIC_SKIPPED,
    UI_METRIC_TOTAL,
    UI_MIME_CSV,
    UI_MIME_TEXT,
    UI_NO_RESULT,
    UI_NO_TESTS_FOUND,
    UI_OUTPUT_HEADER,
    UI_RUN_BUTTON,
    UI_RUN_ERROR,
    UI_RUNNING,
    UI_SOME_FAILED,
    UI_TABLE_HEADER,
    UI_TARGET_LABEL,
    UI_TIMED_OUT,
    UI_VERBOSE_LABEL,
)

STATE_RESULT = "test_run_result"
STATE_STAMP = "test_run_stamp"


def render_test_panel() -> None:
    """Render the Tests tab."""
    st.markdown(UI_HEADER)
    st.caption(UI_INTRO)

    runner = PytestRunner()

    if not runner.has_tests():
        st.info(UI_NO_TESTS_FOUND)
        st.caption(f"Looked in: {runner.tests_dir}")
        return

    target, keyword, verbose = _render_controls(runner)

    if st.button(UI_RUN_BUTTON, type="primary", key="test_panel_run"):
        with st.spinner(UI_RUNNING):
            result = runner.run(
                target=target,
                keyword=keyword,
                verbose=verbose,
            )
        st.session_state[STATE_RESULT] = result
        st.session_state[STATE_STAMP] = datetime.now().strftime(
            FILE_TIMESTAMP_FORMAT
        )

    result = st.session_state.get(STATE_RESULT)

    if result is None:
        st.info(UI_NO_RESULT)
        return

    _render_result(result)


# =====================================================================
# Controls
# =====================================================================
def _render_controls(runner: PytestRunner) -> tuple[str, str, bool]:
    left, middle, right = st.columns([2, 2, 1])

    with left:
        target = st.selectbox(
            UI_TARGET_LABEL,
            options=runner.available_targets(),
            index=0,
            key="test_panel_target",
        )

    with middle:
        keyword = st.text_input(
            UI_KEYWORD_LABEL,
            value="",
            placeholder=UI_KEYWORD_PLACEHOLDER,
            key="test_panel_keyword",
        )

    with right:
        verbose = st.checkbox(
            UI_VERBOSE_LABEL,
            value=False,
            key="test_panel_verbose",
        )

    return target or ALL_TESTS_LABEL, keyword, verbose


# =====================================================================
# Result rendering
# =====================================================================
def _render_result(result: TestRunResult) -> None:
    if result.error:
        st.error(UI_RUN_ERROR.format(reason=result.error))
        return

    if result.timed_out:
        st.error(UI_TIMED_OUT.format(seconds=RUN_TIMEOUT_SECONDS))

    _render_metrics(result)
    _render_verdict(result)
    _render_table(result)
    _render_failures(result)
    _render_downloads(result)
    _render_raw_output(result)


def _render_metrics(result: TestRunResult) -> None:
    columns = st.columns(5)
    columns[0].metric(UI_METRIC_TOTAL, result.total)
    columns[1].metric(UI_METRIC_PASSED, result.passed)
    columns[2].metric(
        UI_METRIC_FAILED,
        result.failed + result.errors,
    )
    columns[3].metric(UI_METRIC_SKIPPED, result.skipped)
    columns[4].metric(UI_METRIC_DURATION, f"{result.duration:.1f}")


def _render_verdict(result: TestRunResult) -> None:
    if result.timed_out:
        return

    if result.is_green:
        st.success(UI_ALL_PASSED)
        return

    st.error(
        UI_SOME_FAILED.format(failed=result.failed + result.errors)
    )


def _render_table(result: TestRunResult) -> None:
    st.markdown(UI_TABLE_HEADER)

    failures_only = st.checkbox(
        UI_FAILURES_ONLY_LABEL,
        value=not result.is_green,
        key="test_panel_failures_only",
    )

    cases = result.failing if failures_only else result.cases
    if not cases:
        st.info(UI_ALL_PASSED)
        return

    rows = [
        {
            COLUMN_OUTCOME: OUTCOME_ICONS.get(case.outcome, case.outcome),
            COLUMN_MODULE: case.module,
            COLUMN_TEST: case.name,
            COLUMN_DURATION: case.duration,
            COLUMN_MESSAGE: _preview(case.message),
        }
        for case in cases
    ]

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_order=list(TABLE_COLUMNS),
    )


def _render_failures(result: TestRunResult) -> None:
    if not result.failing:
        return

    st.markdown(UI_DETAIL_HEADER)

    for index, case in enumerate(result.failing):
        label = f"{OUTCOME_ICONS.get(case.outcome, case.outcome)} | {case.module} | {case.name}"
        with st.expander(label, expanded=index == 0):
            if case.message:
                st.markdown(f"**{case.message}**")
            if case.detail:
                st.code(case.detail, language="text")


def _render_downloads(result: TestRunResult) -> None:
    stamp = st.session_state.get(STATE_STAMP, "")

    left, right = st.columns(2)

    with left:
        st.download_button(
            label=UI_DOWNLOAD_CSV,
            data=_as_csv(result),
            file_name=UI_FILE_CSV.format(stamp=stamp),
            mime=UI_MIME_CSV,
            key="test_panel_download_csv",
        )

    with right:
        st.download_button(
            label=UI_DOWNLOAD_LOG,
            data=_as_log(result),
            file_name=UI_FILE_LOG.format(stamp=stamp),
            mime=UI_MIME_TEXT,
            key="test_panel_download_log",
        )


def _render_raw_output(result: TestRunResult) -> None:
    with st.expander(UI_OUTPUT_HEADER.replace("### ", ""), expanded=False):
        st.markdown(UI_COMMAND_HEADER)
        st.code(result.command, language="text")

        if result.stdout.strip():
            st.code(result.stdout, language="text")

        if result.stderr.strip():
            st.code(result.stderr, language="text")


# =====================================================================
# Serialisation
# =====================================================================
def _as_csv(result: TestRunResult) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(list(TABLE_COLUMNS))

    for case in result.cases:
        writer.writerow(
            [
                case.outcome,
                case.module,
                case.name,
                case.duration,
                case.message.replace("\n", " ").strip(),
            ]
        )

    return buffer.getvalue()


def _as_log(result: TestRunResult) -> str:
    lines = [
        f"Command   : {result.command}",
        f"Started   : {result.started_at}",
        f"Exit code : {result.exit_code}",
        f"Duration  : {result.duration:.2f}s",
        f"Total     : {result.total}",
        f"Passed    : {result.passed}",
        f"Failed    : {result.failed}",
        f"Errors    : {result.errors}",
        f"Skipped   : {result.skipped}",
        "",
        "--- stdout ---",
        result.stdout,
        "",
        "--- stderr ---",
        result.stderr,
    ]
    return "\n".join(lines)


def _preview(text: str) -> str:
    clean = " ".join(str(text or "").split())
    if len(clean) <= MESSAGE_PREVIEW_LENGTH:
        return clean
    return clean[: MESSAGE_PREVIEW_LENGTH - 3] + "..."