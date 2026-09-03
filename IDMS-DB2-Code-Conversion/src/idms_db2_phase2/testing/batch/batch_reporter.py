from __future__ import annotations

from pathlib import Path

from rules.batch_runner_messages import (
    BULLET_TEMPLATE,
    HEADER_DIAGNOSTICS,
    HEADER_VALIDATION_MESSAGES,
    LOG_CONVERSION_COMPLETED_TEMPLATE,
    LOG_INPUT_PROGRAM_TEMPLATE,
    LOG_OUTPUT_FILE_TEMPLATE,
    NO_VALIDATION_MESSAGES,
    PRESERVE_SOURCE_LABEL,
    PRINT_GENERATION_COMPLETED_TEMPLATE,
    PRINT_INPUT_PROGRAM_TEMPLATE,
    PRINT_OUTPUT_CREATED_TEMPLATE,
    SUMMARY_MAPPING_FOLDER_TEMPLATE,
    SUMMARY_MODE_TEMPLATE,
    SUMMARY_OUTPUT_FOLDER_TEMPLATE,
    SUMMARY_PROGRAM_COUNT_TEMPLATE,
    SUMMARY_PROGRAM_FOLDER_TEMPLATE,
    SUMMARY_PROJECT_ROOT_TEMPLATE,
    SUMMARY_SRC_DIR_TEMPLATE,
    SUMMARY_TARGET_PROGRAM_ID_TEMPLATE,
    HEADER_BATCH_INPUT_SUMMARY,
)

from .batch_models import BatchMode


def log_program_result(
    *,
    mode: BatchMode,
    program_path: Path,
    output_path: Path,
    result,
    diagnostics: list[str],
    logger,
) -> None:
    logger.info(LOG_CONVERSION_COMPLETED_TEMPLATE.format(mode=mode.name))
    logger.info(LOG_INPUT_PROGRAM_TEMPLATE.format(path=program_path))
    logger.info(LOG_OUTPUT_FILE_TEMPLATE.format(path=output_path))

    print("")
    print(PRINT_GENERATION_COMPLETED_TEMPLATE.format(mode=mode.name))
    print(PRINT_INPUT_PROGRAM_TEMPLATE.format(path=program_path))
    print(PRINT_OUTPUT_CREATED_TEMPLATE.format(path=output_path))

    print("")
    print(HEADER_VALIDATION_MESSAGES)
    print("")

    if result.validation_messages:
        for message in result.validation_messages:
            print(BULLET_TEMPLATE.format(text=message))
            logger.warning(message)
    else:
        print(NO_VALIDATION_MESSAGES)

    print("")
    print(HEADER_DIAGNOSTICS)
    print("")

    for diagnostic in diagnostics:
        print(BULLET_TEMPLATE.format(text=diagnostic))
        logger.info(diagnostic)


def print_batch_summary(
    *,
    project_root,
    src_dir,
    mode: BatchMode,
    mapping_folder,
    program_count: int,
    target_program_id: str,
) -> None:
    print("")
    print(HEADER_BATCH_INPUT_SUMMARY)
    print("")
    print(SUMMARY_PROJECT_ROOT_TEMPLATE.format(value=project_root))
    print(SUMMARY_SRC_DIR_TEMPLATE.format(value=src_dir))
    print(SUMMARY_MODE_TEMPLATE.format(value=mode.name))
    print(SUMMARY_MAPPING_FOLDER_TEMPLATE.format(value=mapping_folder))
    print(SUMMARY_PROGRAM_FOLDER_TEMPLATE.format(value=mode.program_dir))
    print(SUMMARY_PROGRAM_COUNT_TEMPLATE.format(value=program_count))
    print(SUMMARY_OUTPUT_FOLDER_TEMPLATE.format(value=mode.output_dir))
    print(
        SUMMARY_TARGET_PROGRAM_ID_TEMPLATE.format(
            value=target_program_id or PRESERVE_SOURCE_LABEL
        )
    )