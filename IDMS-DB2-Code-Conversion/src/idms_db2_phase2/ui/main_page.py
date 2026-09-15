# LOCATION: src/idms_db2_phase2/ui/main_page.py
# ACTION: REPLACE ENTIRE FILE

from __future__ import annotations

import streamlit as st

from code_review.ui.review_panel import render_review_panel
from idms_db2_phase2.ui.main_tab import render_main_tab
from idms_db2_phase2.ui.output_tabs import (
    render_diagnostics_tab,
    render_generated_cobol_tab,
    render_sheet_mapping_rows_tab,
    render_validation_tab,
)
from idms_db2_phase2.ui.session_state import initialize_session_state
from idms_db2_phase2.ui.test_panel import render_test_panel
from rules.test_runner_rules import UI_TAB_TITLE as TESTS_TAB_TITLE

TAB_MAIN = "Main"
TAB_SHEET_MAPPING = "Sheet Mapping Rows"
TAB_GENERATED = "Generated DB2 COBOL"
TAB_VALIDATION = "Validation"
TAB_CODE_REVIEW = "Code Review"
TAB_DIAGNOSTICS = "Diagnostics"


def render_main_page() -> None:
    initialize_session_state()

    tabs = st.tabs(
        [
            TAB_MAIN,
            TAB_SHEET_MAPPING,
            TAB_GENERATED,
            TAB_VALIDATION,
            TAB_CODE_REVIEW,
            TAB_DIAGNOSTICS,
            TESTS_TAB_TITLE,
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
        render_review_panel()

    with tabs[5]:
        render_diagnostics_tab()

    with tabs[6]:
        render_test_panel()