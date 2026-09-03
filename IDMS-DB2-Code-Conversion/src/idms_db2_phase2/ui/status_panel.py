from __future__ import annotations

import streamlit as st


def render_current_status() -> None:
    st.markdown("## Current Status")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Sheet Mapping Rows", len(st.session_state.sheet_mapping_rows))

    with col2:
        st.metric("DCLGEN Columns", len(st.session_state.dclgen_columns))

    with col3:
        st.metric("Copybook Fields", len(st.session_state.copybook_fields))

    with col4:
        st.metric("IDMS COBOL Length", len(st.session_state.idms_cobol_text))

    if st.session_state.loaded:
        st.success("Inputs loaded. Review diagnostics before generating.")

    if st.session_state.generated:
        st.success("DB2 COBOL generated. Download is available below.")


def render_main_download_section() -> None:
    st.markdown("## Download Generated Output")

    if not st.session_state.generated or not st.session_state.converted_cobol:
        st.info("Generate DB2 COBOL to enable download.")
        return

    st.success("Generated DB2 COBOL is ready for download.")

    st.caption(
        f"Output file name: `{st.session_state.converted_cobol_file_name}`"
    )

    st.download_button(
        label="Download Generated DB2 COBOL",
        data=st.session_state.converted_cobol,
        file_name=st.session_state.converted_cobol_file_name,
        mime="text/plain",
        type="primary",
        key="main_download_generated_cobol",
    )

    with st.expander("Preview Generated DB2 COBOL", expanded=False):
        st.text_area(
            "Generated DB2 COBOL Preview",
            value=st.session_state.converted_cobol,
            height=500,
            key="main_generated_cobol_preview",
        )