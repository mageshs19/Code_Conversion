from __future__ import annotations

from datetime import datetime
from pathlib import Path

from idms_db2_phase2.domain.models import ConversionInput
from idms_db2_phase2.infrastructure.file_loader import FileLoader
from idms_db2_phase2.infrastructure.local_uploaded_file import LocalUploadedFile
from idms_db2_phase2.orchestration.conversion_service import ConversionService
from rules.batch_runner_messages import (
    DIAG_SOURCE_FILE_TEMPLATE,
    DIAG_SOURCE_LEN_TEMPLATE,
)
from rules.batch_runner_rules import (
    AUTO_FIX_PIC_LENGTH_MISMATCHES_DEFAULT,
    COBOL_TEXT_ENCODING,
    OUTPUT_FILE_EXTENSION,
    OUTPUT_FILE_NAME_TEMPLATE,
    OUTPUT_TIMESTAMP_FORMAT,
)

from .batch_models import BatchMode, SharedInputs
from .batch_reporter import log_program_result
from .update_postprocess_pipeline import apply_update_postprocess


def build_output_path(*, mode: BatchMode, program_path: Path) -> Path:
    timestamp = datetime.now().strftime(OUTPUT_TIMESTAMP_FORMAT)
    file_name = OUTPUT_FILE_NAME_TEMPLATE.format(
        stem=program_path.stem,
        timestamp=timestamp,
        extension=OUTPUT_FILE_EXTENSION,
    )
    return mode.output_dir / file_name


def convert_one_program(
    *,
    mode: BatchMode,
    program_path: Path,
    shared_inputs: SharedInputs,
    target_program_id: str,
    logger,
) -> Path:
    file_loader = FileLoader()
    source_text = file_loader.read_uploaded_text(LocalUploadedFile(program_path))

    diagnostics = list(shared_inputs.diagnostics)
    diagnostics.append(
        DIAG_SOURCE_FILE_TEMPLATE.format(mode=mode.name, path=program_path)
    )
    diagnostics.append(
        DIAG_SOURCE_LEN_TEMPLATE.format(mode=mode.name, length=len(source_text))
    )

    service = ConversionService()
    result = service.convert(
        ConversionInput(
            sheet_mapping_rows=shared_inputs.sheet_rows,
            dclgen_columns=shared_inputs.dclgen_columns,
            copybook_fields=shared_inputs.copybook_fields,
            idms_cobol_text=source_text,
            target_program_id=target_program_id,
            auto_fix_pic_length_mismatches=AUTO_FIX_PIC_LENGTH_MISMATCHES_DEFAULT,
        )
    )

    converted_cobol = result.converted_cobol or ""

    if mode.apply_update_postprocess:
        converted_cobol = apply_update_postprocess(
            source_text=source_text,
            converted_cobol=converted_cobol,
            copybook_fields=shared_inputs.copybook_fields,
            dclgen_columns=shared_inputs.dclgen_columns,
            target_program_id=target_program_id,
            diagnostics=diagnostics,
            logger=logger,
        )

    output_path = build_output_path(mode=mode, program_path=program_path)
    output_path.write_text(converted_cobol, encoding=COBOL_TEXT_ENCODING)

    log_program_result(
        mode=mode,
        program_path=program_path,
        output_path=output_path,
        result=result,
        diagnostics=diagnostics,
        logger=logger,
    )

    return output_path