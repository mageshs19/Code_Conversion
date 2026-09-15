# LOCATION: src/idms_db2_phase2/ui/output_tabs.py
# ACTION: REPLACE ENTIRE FILE

from __future__ import annotations

import csv
import io

import streamlit as st

from idms_db2_phase2.analyzers.metadata_service import MetadataService
from idms_db2_phase2.ui.message_classifier import (
    ClassifiedMessage,
    MessageClassifier,
)
from rules.validation_display_rules import (
    COLUMN_CATEGORY,
    COLUMN_COUNT,
    COLUMN_FILE,
    COLUMN_MESSAGE,
    COLUMN_ROLE,
    COLUMN_SEVERITY,
    MESSAGE_TABLE_COLUMNS,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_ORDER,
    SEVERITY_WARNING,
    UI_CLEAN_RUN,
    UI_DIAGNOSTICS_HEADER,
    UI_DIAGNOSTICS_INTRO,
    UI_DOWNLOAD_DIAGNOSTICS,
    UI_DOWNLOAD_VALIDATION,
    UI_ERRORS_HEADER,
    UI_FILE_DIAGNOSTICS,
    UI_FILE_VALIDATION,
    UI_FILES_EMPTY,
    UI_FILES_HEADER,
    UI_FILTER_CATEGORY,
    UI_FILTER_SEARCH,
    UI_FILTER_SEARCH_PLACEHOLDER,
    UI_FILTER_SEVERITY,
    UI_INFO_CAPTION,
    UI_INFO_HEADER,
    UI_METRIC_ERRORS,
    UI_METRIC_INFO,
    UI_METRIC_TOTAL,
    UI_METRIC_WARNINGS,
    UI_MIME_CSV,
    UI_MIME_TEXT,
    UI_NO_MATCH,
    UI_NO_MESSAGES,
    UI_PARSER_EMPTY,
    UI_PARSER_HEADER,
    UI_RAW_HEADER,
    UI_VALIDATION_HEADER,
    UI_VALIDATION_INTRO,
    UI_WARNINGS_HEADER,
)

_CLASSIFIER = MessageClassifier()


# =====================================================================
# Sheet Mapping tab
# =====================================================================
def render_sheet_mapping_rows_tab() -> None:
    st.markdown("## Sheet Mapping Rows")

    metadata_service = MetadataService()
    rows = metadata_service.mapping_preview_rows(
        st.session_state.sheet_mapping_rows,
    )

    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
        return

    st.info("No Sheet Mapping rows available. Upload Excel or CSV first.")


# =====================================================================
# Generated COBOL tab
# =====================================================================
def render_generated_cobol_tab() -> None:
    st.markdown("## Generated DB2 COBOL")

    if not st.session_state.converted_cobol:
        st.info("Generate DB2 COBOL from the Main tab.")
        return

    st.caption(
        f"Output file name: `{st.session_state.converted_cobol_file_name}`"
    )

    st.download_button(
        label="Download Generated COBOL",
        data=st.session_state.converted_cobol,
        file_name=st.session_state.converted_cobol_file_name,
        mime="text/plain",
        type="primary",
        key="generated_tab_download_generated_cobol",
    )

    st.text_area(
        "Final DB2 COBOL Code",
        value=st.session_state.converted_cobol,
        height=760,
        key="generated_tab_final_db2_cobol_code",
    )


# =====================================================================
# Validation tab
# =====================================================================
def render_validation_tab() -> None:
    """Severity-aware validation report.

    The previous version pushed every message through st.warning(), which
    painted eighty lines of normal pass narration the same colour as a
    genuine failure. Messages are now classified, counted, filtered and
    grouped, so the two lines that need action are visible immediately.
    """
    st.markdown(UI_VALIDATION_HEADER)
    st.caption(UI_VALIDATION_INTRO)

    raw = st.session_state.get("validation_messages") or []
    if not raw:
        st.info(UI_NO_MESSAGES)
        return

    items = _CLASSIFIER.classify_all(list(raw))
    counts = _CLASSIFIER.counts(items)

    _render_metrics(counts, len(items))

    if counts[SEVERITY_ERROR] == 0 and counts[SEVERITY_WARNING] == 0:
        st.success(UI_CLEAN_RUN)

    filtered = _render_filters(items)

    if not filtered:
        st.info(UI_NO_MATCH)
        return

    _render_band(
        items=_CLASSIFIER.of_severity(filtered, SEVERITY_ERROR),
        header=UI_ERRORS_HEADER,
        renderer=st.error,
    )
    _render_band(
        items=_CLASSIFIER.of_severity(filtered, SEVERITY_WARNING),
        header=UI_WARNINGS_HEADER,
        renderer=st.warning,
    )
    _render_info_band(_CLASSIFIER.of_severity(filtered, SEVERITY_INFO))

    st.download_button(
        label=UI_DOWNLOAD_VALIDATION,
        data=_validation_csv(items),
        file_name=UI_FILE_VALIDATION,
        mime=UI_MIME_CSV,
        key="validation_tab_download_csv",
    )


def _render_metrics(counts: dict[str, int], total: int) -> None:
    columns = st.columns(4)
    columns[0].metric(UI_METRIC_ERRORS, counts[SEVERITY_ERROR])
    columns[1].metric(UI_METRIC_WARNINGS, counts[SEVERITY_WARNING])
    columns[2].metric(UI_METRIC_INFO, counts[SEVERITY_INFO])
    columns[3].metric(UI_METRIC_TOTAL, total)


def _render_filters(
    items: list[ClassifiedMessage],
) -> list[ClassifiedMessage]:
    left, middle, right = st.columns([2, 2, 2])

    with left:
        severities = st.multiselect(
            UI_FILTER_SEVERITY,
            options=list(SEVERITY_ORDER),
            default=list(SEVERITY_ORDER),
            key="validation_tab_severity",
        )

    with middle:
        categories = st.multiselect(
            UI_FILTER_CATEGORY,
            options=_CLASSIFIER.categories(items),
            default=[],
            key="validation_tab_category",
        )

    with right:
        search = st.text_input(
            UI_FILTER_SEARCH,
            value="",
            placeholder=UI_FILTER_SEARCH_PLACEHOLDER,
            key="validation_tab_search",
        )

    needle = str(search or "").strip().lower()

    return [
        item
        for item in items
        if item.severity in severities
        and (not categories or item.category in categories)
        and (not needle or needle in item.text.lower())
    ]


def _render_band(
    items: list[ClassifiedMessage],
    header: str,
    renderer,
) -> None:
    if not items:
        return

    st.markdown(header)
    for item in items:
        renderer(item.text)


def _render_info_band(items: list[ClassifiedMessage]) -> None:
    """Narration goes in a collapsed table, never eighty coloured boxes."""
    if not items:
        return

    st.markdown(UI_INFO_HEADER)

    with st.expander(
        UI_INFO_CAPTION.format(count=len(items)),
        expanded=False,
    ):
        st.dataframe(
            [
                {
                    COLUMN_SEVERITY: item.severity,
                    COLUMN_CATEGORY: item.category,
                    COLUMN_MESSAGE: item.text,
                }
                for item in items
            ],
            use_container_width=True,
            hide_index=True,
            column_order=list(MESSAGE_TABLE_COLUMNS),
        )


def _validation_csv(items: list[ClassifiedMessage]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(list(MESSAGE_TABLE_COLUMNS))

    for item in items:
        writer.writerow([item.severity, item.category, item.text])

    return buffer.getvalue()


# =====================================================================
# Diagnostics tab
# =====================================================================
def render_diagnostics_tab() -> None:
    """Parser diagnostics, grouped and searchable.

    Replaces a raw st.json dump plus one unscrollable code block.
    """
    st.markdown(UI_DIAGNOSTICS_HEADER)
    st.caption(UI_DIAGNOSTICS_INTRO)

    _render_uploaded_files()
    _render_parser_diagnostics()


def _render_uploaded_files() -> None:
    st.markdown(UI_FILES_HEADER)

    uploaded = st.session_state.get("uploaded_file_names") or {}
    if not uploaded:
        st.info(UI_FILES_EMPTY)
        return

    rows: list[dict[str, str]] = []
    for role, value in uploaded.items():
        label = str(role).replace("_", " ").title()

        if isinstance(value, (list, tuple, set)):
            for name in value:
                rows.append({COLUMN_ROLE: label, COLUMN_FILE: str(name)})
        elif value:
            rows.append({COLUMN_ROLE: label, COLUMN_FILE: str(value)})

    if not rows:
        st.info(UI_FILES_EMPTY)
        return

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_order=[COLUMN_ROLE, COLUMN_FILE],
    )


def _render_parser_diagnostics() -> None:
    st.markdown(UI_PARSER_HEADER)

    diagnostics = st.session_state.get("diagnostics") or []
    if not diagnostics:
        st.info(UI_PARSER_EMPTY)
        return

    items = _CLASSIFIER.classify_all(list(diagnostics))

    summary: dict[str, int] = {}
    for item in items:
        summary[item.category] = summary.get(item.category, 0) + 1

    st.dataframe(
        [
            {COLUMN_CATEGORY: category, COLUMN_COUNT: count}
            for category, count in sorted(summary.items())
        ],
        use_container_width=True,
        hide_index=True,
        column_order=[COLUMN_CATEGORY, COLUMN_COUNT],
    )

    search = st.text_input(
        UI_FILTER_SEARCH,
        value="",
        placeholder=UI_FILTER_SEARCH_PLACEHOLDER,
        key="diagnostics_tab_search",
    )

    needle = str(search or "").strip().lower()
    visible = [
        item for item in items
        if not needle or needle in item.text.lower()
    ]

    if not visible:
        st.info(UI_NO_MATCH)
    else:
        st.dataframe(
            [
                {
                    COLUMN_CATEGORY: item.category,
                    COLUMN_MESSAGE: item.text,
                }
                for item in visible
            ],
            use_container_width=True,
            hide_index=True,
            column_order=[COLUMN_CATEGORY, COLUMN_MESSAGE],
        )

    with st.expander(UI_RAW_HEADER, expanded=False):
        st.code("\n".join(str(line) for line in diagnostics), language="text")

    st.download_button(
        label=UI_DOWNLOAD_DIAGNOSTICS,
        data="\n".join(str(line) for line in diagnostics),
        file_name=UI_FILE_DIAGNOSTICS,
        mime=UI_MIME_TEXT,
        key="diagnostics_tab_download",
    )