from __future__ import annotations

from idms_db2_phase2.composers.fixed_format_composer import FixedFormatComposer
from idms_db2_phase2.composers.procedure_indent_normalizer import (
    ProcedureIndentNormalizer,
)
from idms_db2_phase2.postprocess.update_char_literal_quoter import (
    UpdateCharLiteralQuoter,
)
from idms_db2_phase2.postprocess.update_date_host_converter import (
    UpdateDateHostConverter,
)
from idms_db2_phase2.postprocess.update_final_cleanup import UpdateFinalCleanup
from idms_db2_phase2.postprocess.update_input_record_renamer import (
    UpdateInputRecordRenamer,
)
from idms_db2_phase2.postprocess.update_program_enhancer import UpdateProgramEnhancer
from idms_db2_phase2.services.fixed_format_line_service import FixedFormatLineService
from idms_db2_phase2.services.name_derivation_resolver import NameDerivationResolver
from idms_db2_phase2.services.update_audit_move_inserter import (
    UpdateAuditMoveInserter,
)
from idms_db2_phase2.services.update_cobol_final_cleanup_utils import (
    UpdateCobolFinalCleanupUtils,
)
from patterns.batch_runner_patterns import COPY_NAME_PATTERN
from rules.update_runner_messages import (
    DIAG_UPDATE_AUDIT_MOVES,
    DIAG_UPDATE_ENHANCEMENT_DONE,
    DIAG_UPDATE_SKIPPED_TEMPLATE,
    LOG_UPDATE_ENHANCEMENT_DONE,
)


def derive_input_record_rename(converted_cobol: str) -> tuple[str, str]:
    """Recover (old, new) input-record names from COPY statements.

    Applies the VM...BD...->VMDZ derivation. Returns ("", "") when no
    derivable COPY name is found. No name is hardcoded.
    """
    deriver = NameDerivationResolver()

    copy_names = COPY_NAME_PATTERN.findall(str(converted_cobol or ""))

    for raw in copy_names:
        name = str(raw or "").strip().upper()
        if not name:
            continue
        if deriver.is_derivable(name):
            derived = deriver.derive(name)
            if derived != name:
                return name, derived

    return "", ""


def enhance_update_program(
    *,
    source_cobol: str,
    converted_cobol: str,
    copybook_fields: list,
    dclgen_columns: list,
    target_program_id: str,
    diagnostics: list[str],
    logger,
) -> str:
    try:
        enhancer = UpdateProgramEnhancer()
        enhanced_result = enhancer.enhance(
            source_cobol=source_cobol,
            converted_cobol=converted_cobol,
            copybook_fields=copybook_fields,
            dclgen_columns=dclgen_columns,
            target_program_id=target_program_id,
        )

        diagnostics.extend(enhanced_result.diagnostics)
        diagnostics.append(DIAG_UPDATE_ENHANCEMENT_DONE)
        logger.info(LOG_UPDATE_ENHANCEMENT_DONE)

        fixed = FixedFormatComposer().format(enhanced_result.converted_cobol)
        cleaned = UpdateFinalCleanup().apply(fixed)
        formatted = FixedFormatComposer().format(cleaned)

        _ff = FixedFormatLineService()
        _audit = UpdateAuditMoveInserter(
            fixed_format=_ff,
            utils=UpdateCobolFinalCleanupUtils(_ff),
        )
        with_audit = _audit.insert_update_audit_moves(formatted)

        if with_audit != formatted:
            diagnostics.append(DIAG_UPDATE_AUDIT_MOVES)

        with_char = UpdateCharLiteralQuoter(dclgen_columns).apply(
            with_audit,
            diagnostics,
        )
        with_dates = UpdateDateHostConverter(dclgen_columns).apply(
            with_char,
            diagnostics,
        )

        old_record, new_record = derive_input_record_rename(with_dates)

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

    except Exception as exc:
        message = DIAG_UPDATE_SKIPPED_TEMPLATE.format(reason=exc)
        diagnostics.append(message)
        logger.exception(message)
        return converted_cobol