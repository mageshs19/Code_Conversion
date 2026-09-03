from __future__ import annotations

import streamlit as st

from idms_db2_phase2.ui.main_tab import render_main_tab
from idms_db2_phase2.ui.output_tabs import (
    render_diagnostics_tab,
    render_generated_cobol_tab,
    render_sheet_mapping_rows_tab,
    render_validation_tab,
)
from idms_db2_phase2.ui.session_state import initialize_session_state


def render_main_page() -> None:
    initialize_session_state()

    tabs = st.tabs(
        [
            "Main",
            "Sheet Mapping Rows",
            "Generated DB2 COBOL",
            "Validation",
            "Diagnostics",
        ]
    )

    with tabs[0]:
        render_main_tab()

    with tabs[1]:
        render_sheet_mapping_rows_tab()

    with tabs[2]:
        render_generated_cobol_tab()

    with tabs[3]:
        render_validation_tab()

    with tabs[4]:
        render_diagnostics_tab()