from __future__ import annotations

import re

import streamlit as st

from idms_db2_phase2.domain.models import ConversionInput
from idms_db2_phase2.orchestration.conversion_service import ConversionService
from idms_db2_phase2.parsers.cobol_parser import CobolParser
from idms_db2_phase2.services.name_derivation_resolver import NameDerivationResolver
from idms_db2_phase2.ui.file_name_utils import build_converted_cobol_file_name


# Detects any IDMS write verb in the SOURCE program (STORE/MODIFY/ERASE).
# If present, this is an update program and needs the update post-process.
_IDMS_WRITE_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?(STORE|MODIFY|ERASE)\b",
    flags=re.IGNORECASE | re.MULTILINE,
)


def resolve_target_program_id(source_text: str) -> str:
    """Derive the target PROGRAM-ID from the uploaded COBOL source.

    Applies the project's VM...BD... -> VMDZ... rule (e.g. VM4BD420 -> VMDZ4420).
    Returns "" when no PROGRAM-ID is detected, so the converter preserves the
    source PROGRAM-ID instead of forcing a literal.
    """
    source_id = CobolParser().program_id(source_text)
    if not source_id:
        return ""
    return NameDerivationResolver().derive(source_id)


def _is_update_program(source_text: str) -> bool:
    """True when the source contains IDMS write verbs (STORE/MODIFY/ERASE)."""
    return bool(_IDMS_WRITE_PATTERN.search(str(source_text or "")))


def _apply_update_postprocess(
    *,
    source_text: str,
    converted_cobol: str,
    copybook_fields: list,
    dclgen_columns: list,
    target_program_id: str,
    diagnostics: list[str],
) -> str:
    """Run the update-only enhancement pipeline (restart flow, SQLERROR fix,
    DCLGEN includes, audit moves, CHAR/date host conversion, final cleanup).

    Mirrors testing/update/update_postprocess_pipeline.enhance_update_program
    but is import-light for the Streamlit context. Any failure returns the
    base converted COBOL unchanged.
    """
    try:
        from idms_db2_phase2.composers.fixed_format_composer import (
            FixedFormatComposer,
        )
        from idms_db2_phase2.composers.procedure_indent_normalizer import (
            ProcedureIndentNormalizer,
        )
        from idms_db2_phase2.postprocess.update_char_literal_quoter import (
            UpdateCharLiteralQuoter,
        )
        from idms_db2_phase2.postprocess.update_date_host_converter import (
            UpdateDateHostConverter,
        )
        from idms_db2_phase2.postprocess.update_final_cleanup import (
            UpdateFinalCleanup,
        )
        from idms_db2_phase2.postprocess.update_input_record_renamer import (
            UpdateInputRecordRenamer,
        )
        from idms_db2_phase2.postprocess.update_program_enhancer import (
            UpdateProgramEnhancer,
        )
        from idms_db2_phase2.services.fixed_format_line_service import (
            FixedFormatLineService,
        )
        from idms_db2_phase2.services.update_audit_move_inserter import (
            UpdateAuditMoveInserter,
        )
        from idms_db2_phase2.services.update_cobol_final_cleanup_utils import (
            UpdateCobolFinalCleanupUtils,
        )
        from patterns.batch_runner_patterns import COPY_NAME_PATTERN
        from idms_db2_phase2.services.name_derivation_resolver import (
            NameDerivationResolver,
        )

        enhanced = UpdateProgramEnhancer().enhance(
            source_cobol=source_text,
            converted_cobol=converted_cobol,
            copybook_fields=copybook_fields,
            dclgen_columns=dclgen_columns,
            target_program_id=target_program_id,
        )
        diagnostics.extend(enhanced.diagnostics)

        fixed = FixedFormatComposer().format(enhanced.converted_cobol)
        cleaned = UpdateFinalCleanup().apply(fixed)
        formatted = FixedFormatComposer().format(cleaned)

        _ff = FixedFormatLineService()
        with_audit = UpdateAuditMoveInserter(
            fixed_format=_ff,
            utils=UpdateCobolFinalCleanupUtils(_ff),
        ).insert_update_audit_moves(formatted)

        with_char = UpdateCharLiteralQuoter(dclgen_columns).apply(
            with_audit, diagnostics
        )
        with_dates = UpdateDateHostConverter(dclgen_columns).apply(
            with_char, diagnostics
        )

        # Rename original input-record refs to the derived VM...BD...->VMDZ name.
        deriver = NameDerivationResolver()
        old_record = new_record = ""
        for raw in COPY_NAME_PATTERN.findall(str(with_dates or "")):
            name = str(raw or "").strip().upper()
            if name and deriver.is_derivable(name):
                derived = deriver.derive(name)
                if derived != name:
                    old_record, new_record = name, derived
                    break

        if old_record and new_record and old_record != new_record:
            with_renamed = UpdateInputRecordRenamer().apply(
                with_dates,
                old_name=old_record,
                new_name=new_record,
                diagnostics=diagnostics,
            )
        else:
            with_renamed = with_dates

        formatted_final = FixedFormatComposer().format(with_renamed)

        _indent = ProcedureIndentNormalizer()
        normalized = _indent.compose(formatted_final)
        if getattr(_indent, "messages", None):
            diagnostics.extend(_indent.messages)

        return FixedFormatComposer().format(normalized)

    except Exception as exc:  # noqa: BLE001
        diagnostics.append(
            "Update postprocess enhancement skipped. Base converted COBOL "
            f"will be used. Reason: {exc}"
        )
        return converted_cobol


def generate_db2_cobol() -> None:
    if not _validate_generation_inputs():
        return

    idms_cobol_text = st.session_state.idms_cobol_text
    target_program_id = resolve_target_program_id(idms_cobol_text)

    service = ConversionService()
    result = service.convert(
        ConversionInput(
            sheet_mapping_rows=st.session_state.sheet_mapping_rows,
            dclgen_columns=st.session_state.dclgen_columns,
            copybook_fields=st.session_state.copybook_fields,
            idms_cobol_text=idms_cobol_text,
            target_program_id=target_program_id,
        )
    )

    converted_cobol = result.converted_cobol or ""
    validation_messages = list(result.validation_messages or [])

    program_kind = "retrieval"
    if converted_cobol and _is_update_program(idms_cobol_text):
        program_kind = "update"
        converted_cobol = _apply_update_postprocess(
            source_text=idms_cobol_text,
            converted_cobol=converted_cobol,
            copybook_fields=st.session_state.copybook_fields,
            dclgen_columns=st.session_state.dclgen_columns,
            target_program_id=target_program_id,
            diagnostics=validation_messages,
        )

    st.session_state.converted_cobol = converted_cobol
    st.session_state.validation_messages = validation_messages
    st.session_state.operations = result.operations or []

    st.session_state.converted_cobol_file_name = build_converted_cobol_file_name(
        target_program_id=target_program_id,
        source_file_name=st.session_state.idms_cobol_source_name,
    )

    st.session_state.generated = bool(st.session_state.converted_cobol)

    if st.session_state.generated:
        st.success(
            f"DB2 COBOL generated ({program_kind} program, PROGRAM-ID: "
            f"{target_program_id or '(preserved from source)'}). "
            "Download is now available in the Main tab."
        )
    else:
        st.warning(
            "DB2 COBOL was not generated. "
            "Review the Validation and Diagnostics tabs."
        )


def _validate_generation_inputs() -> bool:
    if not st.session_state.loaded:
        st.warning("Load and analyze valid inputs before generating DB2 COBOL.")
        return False

    if not st.session_state.sheet_mapping_rows:
        st.error("Sheet Mapping rows are empty. Reload Sheet Mapping input.")
        return False

    if not st.session_state.dclgen_columns:
        st.error("DCLGEN columns are empty. Reload DCLGEN input.")
        return False

    if not st.session_state.idms_cobol_text.strip():
        st.error("IDMS COBOL source is empty. Reload COBOL input.")
        return False

    return True