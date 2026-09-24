# LOCATION: src/idms_db2_phase2/testing/batch/program_converter.py
# ACTION: REPLACE ENTIRE FILE

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from idms_db2_phase2.domain.models import ConversionInput
from idms_db2_phase2.infrastructure.file_loader import FileLoader
from idms_db2_phase2.infrastructure.local_uploaded_file import LocalUploadedFile
from idms_db2_phase2.orchestration.conversion_service import ConversionService
from patterns.lrf_patterns import COPY_IDMS_LR_PATTERN
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
from rules.lrf_rules import (
    DIAG_LRF_NO_RECORDS_IN_SCOPE,
    DIAG_LRF_RECORDS_IN_SCOPE_TEMPLATE,
    LOG_LRF_TOTAL_RECORDS,
    LRF_VALIDATION_MESSAGES,
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


# ---------------------------------------------------------------------------
# LRF (Logical Record Facility)
# ---------------------------------------------------------------------------
def _logical_records(shared_inputs: SharedInputs) -> list:
    """LRF logical records from the shared inputs.

    Read with getattr so a SharedInputs instance created before the LRF
    field existed still converts without raising AttributeError.
    """
    return list(getattr(shared_inputs, "logical_records", None) or [])


def _source_uses_logical_records(source_text: str) -> list[str]:
    """Logical record names the SOURCE program copies via COPY IDMS LR."""
    names: list[str] = []
    for raw_line in str(source_text or "").splitlines():
        match = COPY_IDMS_LR_PATTERN.search(raw_line)
        if not match:
            continue
        name = str(match.group("lr") or "").strip().upper()
        if name and name not in names:
            names.append(name)
    return names


def _narrate_lrf(
    *,
    source_text: str,
    logical_records: list,
    diagnostics: list[str],
    logger,
) -> None:
    """Record what LRF metadata this program run will see.

    Never raises and never blocks the batch. A program that copies a
    logical record without a matching LRF subschema is reported once, so
    the gap is visible in the run log instead of failing silently.
    """
    if logical_records:
        names = ", ".join(
            str(getattr(record, "logical_record_name", "") or "")
            for record in logical_records
        )
        diagnostics.append(
            DIAG_LRF_RECORDS_IN_SCOPE_TEMPLATE.format(
                count=len(logical_records),
                names=names,
            )
        )
    else:
        diagnostics.append(DIAG_LRF_NO_RECORDS_IN_SCOPE)

    logger.info(LOG_LRF_TOTAL_RECORDS, len(logical_records))

    used = _source_uses_logical_records(source_text)
    if used and not logical_records:
        message = LRF_VALIDATION_MESSAGES["missing_lrf"]
        diagnostics.append(message)
        logger.warning(message)


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

    logical_records = _logical_records(shared_inputs)
    _narrate_lrf(
        source_text=source_text,
        logical_records=logical_records,
        diagnostics=diagnostics,
        logger=logger,
    )

    service = ConversionService()
    result = service.convert(
        ConversionInput(
            sheet_mapping_rows=shared_inputs.sheet_rows,
            dclgen_columns=shared_inputs.dclgen_columns,
            copybook_fields=shared_inputs.copybook_fields,
            logical_records=logical_records,
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