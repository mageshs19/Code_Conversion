from __future__ import annotations

from datetime import datetime
from pathlib import Path

from idms_db2_phase2.domain.models import ConversionInput
from idms_db2_phase2.infrastructure.file_loader import FileLoader
from idms_db2_phase2.infrastructure.local_uploaded_file import LocalUploadedFile
from idms_db2_phase2.orchestration.conversion_service import ConversionService
from idms_db2_phase2.parsers.cobol_parser import CobolParser
from idms_db2_phase2.services.name_derivation_resolver import NameDerivationResolver
from rules.update_runner_messages import (
    BULLET_TEMPLATE,
    DIAG_DERIVED_PROGRAM_ID_TEMPLATE,
    DIAG_SOURCE_FILE_TEMPLATE,
    DIAG_SOURCE_LEN_TEMPLATE,
    HEADER_DIAGNOSTICS,
    HEADER_INPUT_SUMMARY,
    HEADER_SELECTED_INPUT_FILES,
    HEADER_VALIDATION_MESSAGES,
    LOG_DERIVED_PROGRAM_ID,
    LOG_GENERATION_COMPLETED,
    LOG_OUTPUT_CREATED,
    LOG_SOURCE_FILE,
    LOG_SOURCE_LEN,
    NO_VALIDATION_MESSAGES,
    PRESERVE_SOURCE_LABEL,
    PRINT_GENERATION_COMPLETED,
    PRINT_INPUT_PROGRAM_TEMPLATE,
    PRINT_OUTPUT_CREATED_TEMPLATE,
    RULE_DIAGNOSTICS,
    RULE_INPUT_SUMMARY,
    RULE_SELECTED_INPUT_FILES,
    RULE_VALIDATION_MESSAGES,
    SELECTED_COBOL_SOURCE_TEMPLATE,
    SELECTED_COPYBOOK_HEADER,
    SELECTED_COPYBOOK_NONE,
    SELECTED_DCLGEN_HEADER,
    SELECTED_PATH_BULLET_TEMPLATE,
    SELECTED_SHEET_MAPPING_TEMPLATE,
    SUMMARY_COBOL_LEN_TEMPLATE,
    SUMMARY_COPYBOOK_FIELDS_TEMPLATE,
    SUMMARY_DCLGEN_COLUMNS_TEMPLATE,
    SUMMARY_PROJECT_ROOT_TEMPLATE,
    SUMMARY_SHEET_ROWS_TEMPLATE,
    SUMMARY_SRC_DIR_TEMPLATE,
    SUMMARY_TARGET_PROGRAM_ID_TEMPLATE,
)
from rules.update_runner_rules import (
    AUTO_FIX_PIC_LENGTH_MISMATCHES_DEFAULT,
    COBOL_TEXT_ENCODING,
    OUTPUT_FILE_EXTENSION,
    OUTPUT_FILE_NAME_TEMPLATE,
    OUTPUT_TIMESTAMP_FORMAT,
)

from .update_input_selector import (
    selected_copybook_paths,
    selected_dclgen_paths,
    selected_mapping_sheet_path,
)
from .update_postprocess_pipeline import enhance_update_program


def resolve_target_program_id(source_text: str) -> str:
    """Derive the target PROGRAM-ID from the source (VM...BD... -> VMDZ...)."""
    source_id = CobolParser().program_id(source_text)
    if not source_id:
        return ""
    return NameDerivationResolver().derive(source_id)


def _build_output_path(output_dir: Path, program_path: Path) -> Path:
    timestamp = datetime.now().strftime(OUTPUT_TIMESTAMP_FORMAT)
    file_name = OUTPUT_FILE_NAME_TEMPLATE.format(
        stem=program_path.stem,
        timestamp=timestamp,
        extension=OUTPUT_FILE_EXTENSION,
    )
    return output_dir / file_name


def _print_summary(*, program_path, sheet_rows, dclgen_columns, copybook_fields,
                   idms_len, target_program_id, project_root, src_dir):
    print("")
    print(HEADER_INPUT_SUMMARY)
    print(RULE_INPUT_SUMMARY)
    print(SUMMARY_PROJECT_ROOT_TEMPLATE.format(value=project_root))
    print(SUMMARY_SRC_DIR_TEMPLATE.format(value=src_dir))
    print(SUMMARY_SHEET_ROWS_TEMPLATE.format(value=len(sheet_rows)))
    print(SUMMARY_DCLGEN_COLUMNS_TEMPLATE.format(value=len(dclgen_columns)))
    print(SUMMARY_COPYBOOK_FIELDS_TEMPLATE.format(value=len(copybook_fields)))
    print(SUMMARY_COBOL_LEN_TEMPLATE.format(value=idms_len))
    print(
        SUMMARY_TARGET_PROGRAM_ID_TEMPLATE.format(
            value=target_program_id or PRESERVE_SOURCE_LABEL
        )
    )

    print("")
    print(HEADER_SELECTED_INPUT_FILES)
    print(RULE_SELECTED_INPUT_FILES)
    print(SELECTED_SHEET_MAPPING_TEMPLATE.format(value=selected_mapping_sheet_path()))
    print(SELECTED_COBOL_SOURCE_TEMPLATE.format(value=program_path))

    print(SELECTED_DCLGEN_HEADER)
    for path in selected_dclgen_paths():
        print(SELECTED_PATH_BULLET_TEMPLATE.format(value=path))

    copybooks = selected_copybook_paths()
    if copybooks:
        print(SELECTED_COPYBOOK_HEADER)
        for path in copybooks:
            print(SELECTED_PATH_BULLET_TEMPLATE.format(value=path))
    else:
        print(SELECTED_COPYBOOK_NONE)


def _print_results(result, diagnostics, logger):
    print("")
    print(HEADER_VALIDATION_MESSAGES)
    print(RULE_VALIDATION_MESSAGES)

    if result.validation_messages:
        for message in result.validation_messages:
            print(BULLET_TEMPLATE.format(text=message))
            logger.warning(message)
    else:
        print(NO_VALIDATION_MESSAGES)

    print("")
    print(HEADER_DIAGNOSTICS)
    print(RULE_DIAGNOSTICS)

    for diagnostic in diagnostics:
        print(BULLET_TEMPLATE.format(text=diagnostic))
        logger.info(diagnostic)


def convert_one_program(
    *,
    program_path: Path,
    sheet_rows: list,
    dclgen_columns: list,
    copybook_fields: list,
    shared_diagnostics: list[str],
    output_dir: Path,
    project_root,
    src_dir,
    logger,
) -> Path:
    file_loader = FileLoader()
    idms_cobol_text = file_loader.read_uploaded_text(LocalUploadedFile(program_path))

    target_program_id = resolve_target_program_id(idms_cobol_text)
    display_id = target_program_id or PRESERVE_SOURCE_LABEL

    diagnostics = list(shared_diagnostics)
    diagnostics.append(DIAG_SOURCE_FILE_TEMPLATE.format(path=program_path))
    diagnostics.append(DIAG_SOURCE_LEN_TEMPLATE.format(length=len(idms_cobol_text)))
    diagnostics.append(DIAG_DERIVED_PROGRAM_ID_TEMPLATE.format(value=display_id))

    logger.info(LOG_SOURCE_FILE, program_path)
    logger.info(LOG_SOURCE_LEN, len(idms_cobol_text))
    logger.info(LOG_DERIVED_PROGRAM_ID, display_id)

    result = ConversionService().convert(
        ConversionInput(
            sheet_mapping_rows=sheet_rows,
            dclgen_columns=dclgen_columns,
            copybook_fields=copybook_fields,
            idms_cobol_text=idms_cobol_text,
            target_program_id=target_program_id,
            auto_fix_pic_length_mismatches=AUTO_FIX_PIC_LENGTH_MISMATCHES_DEFAULT,
        )
    )

    converted_cobol = enhance_update_program(
        source_cobol=idms_cobol_text,
        converted_cobol=result.converted_cobol or "",
        copybook_fields=copybook_fields,
        dclgen_columns=dclgen_columns,
        target_program_id=target_program_id,
        diagnostics=diagnostics,
        logger=logger,
    )

    output_cobol_path = _build_output_path(output_dir, program_path)
    output_cobol_path.write_text(converted_cobol, encoding=COBOL_TEXT_ENCODING)

    logger.info(LOG_GENERATION_COMPLETED)
    logger.info(LOG_OUTPUT_CREATED, output_cobol_path)

    print("")
    print(PRINT_GENERATION_COMPLETED)
    print(PRINT_INPUT_PROGRAM_TEMPLATE.format(path=program_path))
    print(PRINT_OUTPUT_CREATED_TEMPLATE.format(path=output_cobol_path))

    _print_summary(
        program_path=program_path,
        sheet_rows=sheet_rows,
        dclgen_columns=dclgen_columns,
        copybook_fields=copybook_fields,
        idms_len=len(idms_cobol_text),
        target_program_id=target_program_id,
        project_root=project_root,
        src_dir=src_dir,
    )
    _print_results(result, diagnostics, logger)

    return output_cobol_path