from __future__ import annotations

import streamlit as st

from idms_db2_phase2.ui.conversion_actions import generate_db2_cobol
from idms_db2_phase2.ui.input_loader import load_and_analyze_inputs
from idms_db2_phase2.ui.status_panel import (
    render_current_status,
    render_main_download_section,
)


def render_main_tab() -> None:
    st.markdown("## Upload Inputs")

    st.info(
        "Upload Sheet Mapping, one or more DCLGEN files, optional Copybook files, "
        "and the IDMS COBOL source text file to generate DB2 embedded SQL COBOL."
    )

    sheet_mapping_file, dclgen_files, copybook_files, idms_cobol_source_file = (
        _render_uploaders()
    )

    st.caption(
        "Target PROGRAM-ID is derived automatically from the uploaded COBOL "
        "source (VM...BD... -> VMDZ... rule). No manual entry required."
    )

    _render_action_buttons(
        sheet_mapping_file=sheet_mapping_file,
        dclgen_files=dclgen_files,
        copybook_files=copybook_files,
        idms_cobol_source_file=idms_cobol_source_file,
    )

    render_current_status()
    render_main_download_section()


def _render_uploaders():
    col1, col2 = st.columns(2)

    with col1:
        sheet_mapping_file = st.file_uploader(
            "Sheet Mapping Excel or CSV",
            type=["xlsx", "csv"],
            key="sheet_mapping_file",
            help=(
                "Upload Sheet Mapping as .xlsx or .csv. "
                "If your file is .xls, save it as .xlsx or .csv first."
            ),
        )

        dclgen_files = st.file_uploader(
            "DCLGEN text file or files",
            type=["txt", "cbl", "cpy"],
            accept_multiple_files=True,
            key="dclgen_files",
        )

    with col2:
        copybook_files = st.file_uploader(
            "Optional Copybook text file or files",
            type=["txt", "cbl", "cpy"],
            accept_multiple_files=True,
            key="copybook_files",
        )

        idms_cobol_source_file = st.file_uploader(
            "IDMS COBOL source code",
            type=["txt", "cbl", "cob"],
            key="idms_cobol_source_file",
        )

    return (
        sheet_mapping_file,
        dclgen_files,
        copybook_files,
        idms_cobol_source_file,
    )


def _render_action_buttons(
    *,
    sheet_mapping_file,
    dclgen_files,
    copybook_files,
    idms_cobol_source_file,
) -> None:
    col_load, col_generate = st.columns(2)

    with col_load:
        if st.button("Load and Analyze Inputs", type="primary"):
            load_and_analyze_inputs(
                sheet_mapping_file=sheet_mapping_file,
                dclgen_files=dclgen_files,
                copybook_files=copybook_files,
                idms_cobol_source_file=idms_cobol_source_file,
            )

    with col_generate:
        if st.button("Generate DB2 COBOL"):
            generate_db2_cobol()