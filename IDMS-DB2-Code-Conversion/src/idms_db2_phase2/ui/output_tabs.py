from __future__ import annotations

import streamlit as st

from idms_db2_phase2.analyzers.metadata_service import MetadataService


def render_sheet_mapping_rows_tab() -> None:
    st.markdown("## Sheet Mapping Rows")

    metadata_service = MetadataService()

    rows = metadata_service.mapping_preview_rows(
        st.session_state.sheet_mapping_rows,
    )

    if rows:
        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No Sheet Mapping rows available. Upload Excel or CSV first.")


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


def render_validation_tab() -> None:
    st.markdown("## Validation")

    if not st.session_state.validation_messages:
        st.success("No validation messages.")
        return

    for message in st.session_state.validation_messages:
        st.warning(message)


def render_diagnostics_tab() -> None:
    st.markdown("## Diagnostics")

    st.markdown("### Uploaded Files")
    st.json(st.session_state.uploaded_file_names)

    st.markdown("### Parser Diagnostics")

    diagnostics = st.session_state.diagnostics or []

    if not diagnostics:
        st.info("No diagnostics available. Click Load and Analyze Inputs first.")
        return

    st.code(
        "\n".join(diagnostics),
        language="text",
    )