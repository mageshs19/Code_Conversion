from __future__ import annotations

from config.path_settings import DEFAULT_DCLGEN_DIR, DEFAULT_MAPPING_SHEET_DIR
from idms_db2_phase2.infrastructure.file_loader import FileLoader
from idms_db2_phase2.infrastructure.local_uploaded_file import LocalUploadedFile
from idms_db2_phase2.parsers.copybook_parser import CopybookParser
from idms_db2_phase2.parsers.dclgen_parser import DclgenParser
from idms_db2_phase2.parsers.sheet_mapping_parser import SheetMappingParser
from rules.update_runner_messages import (
    COPYBOOK_SOURCE_LABEL,
    DCLGEN_SOURCE_LABEL_TEMPLATE,
    DIAG_COPYBOOK_FILE_COUNT_TEMPLATE,
    DIAG_COPYBOOK_FILE_TEMPLATE,
    DIAG_COPYBOOK_TEXT_LEN_TEMPLATE,
    DIAG_COPYBOOK_TOTAL_FIELDS_TEMPLATE,
    DIAG_DCLGEN_FILE_COUNT_TEMPLATE,
    DIAG_DCLGEN_FILE_TEMPLATE,
    DIAG_DCLGEN_FOLDER_TEMPLATE,
    DIAG_DCLGEN_TEXT_LEN_TEMPLATE,
    DIAG_DCLGEN_TOTAL_COLUMNS_TEMPLATE,
    DIAG_MAPPING_FOLDER_TEMPLATE,
    DIAG_MAPPING_ROWS_TEMPLATE,
    DIAG_MAPPING_SELECTED_TEMPLATE,
    DIAG_START_LOAD_INPUTS,
    LOG_COPYBOOK_FILE,
    LOG_COPYBOOK_FILE_COUNT,
    LOG_COPYBOOK_TEXT_LEN,
    LOG_COPYBOOK_TOTAL_FIELDS,
    LOG_DCLGEN_FILE,
    LOG_DCLGEN_FILE_COUNT,
    LOG_DCLGEN_TEXT_LEN,
    LOG_DCLGEN_TOTAL_COLUMNS,
    LOG_MAPPING_ROWS,
    LOG_MAPPING_SELECTED,
)

from .update_input_selector import (
    selected_copybook_paths,
    selected_dclgen_paths,
    selected_mapping_sheet_path,
)


def _load_mapping_rows(sheet_parser, diagnostics, logger):
    sheet_path = selected_mapping_sheet_path()
    sheet_rows = sheet_parser.parse_uploaded_file(LocalUploadedFile(sheet_path))

    diagnostics.append(
        DIAG_MAPPING_FOLDER_TEMPLATE.format(folder=DEFAULT_MAPPING_SHEET_DIR)
    )
    diagnostics.append(DIAG_MAPPING_SELECTED_TEMPLATE.format(path=sheet_path))
    diagnostics.append(DIAG_MAPPING_ROWS_TEMPLATE.format(count=len(sheet_rows)))
    logger.info(LOG_MAPPING_SELECTED, sheet_path)
    logger.info(LOG_MAPPING_ROWS, len(sheet_rows))

    if hasattr(sheet_parser, "diagnostics"):
        diagnostics.extend(sheet_parser.diagnostics)

    return sheet_rows


def _load_dclgen_columns(dclgen_parser, file_loader, diagnostics, logger):
    dclgen_files = selected_dclgen_paths()
    dclgen_texts: list[str] = []

    diagnostics.append(DIAG_DCLGEN_FOLDER_TEMPLATE.format(folder=DEFAULT_DCLGEN_DIR))
    diagnostics.append(
        DIAG_DCLGEN_FILE_COUNT_TEMPLATE.format(count=len(dclgen_files))
    )
    logger.info(LOG_DCLGEN_FILE_COUNT, len(dclgen_files))

    for index, path in enumerate(dclgen_files, start=1):
        text = file_loader.read_uploaded_text(LocalUploadedFile(path))
        dclgen_texts.append(text)
        diagnostics.append(DIAG_DCLGEN_FILE_TEMPLATE.format(index=index, path=path))
        diagnostics.append(
            DIAG_DCLGEN_TEXT_LEN_TEMPLATE.format(index=index, length=len(text))
        )
        logger.info(LOG_DCLGEN_FILE, index, path)
        logger.info(LOG_DCLGEN_TEXT_LEN, index, len(text))

    if hasattr(dclgen_parser, "parse_many_texts"):
        dclgen_columns = dclgen_parser.parse_many_texts(dclgen_texts)
    else:
        dclgen_columns = []
        for index, text in enumerate(dclgen_texts, start=1):
            dclgen_columns.extend(
                dclgen_parser.parse(
                    text=text,
                    source_label=DCLGEN_SOURCE_LABEL_TEMPLATE.format(index=index),
                )
            )

    diagnostics.append(
        DIAG_DCLGEN_TOTAL_COLUMNS_TEMPLATE.format(count=len(dclgen_columns))
    )
    logger.info(LOG_DCLGEN_TOTAL_COLUMNS, len(dclgen_columns))

    if hasattr(dclgen_parser, "diagnostics"):
        diagnostics.extend(dclgen_parser.diagnostics)

    return dclgen_columns


def _load_copybook_fields(copybook_parser, file_loader, diagnostics, logger):
    copybook_files = selected_copybook_paths()
    text_parts: list[str] = []

    diagnostics.append(
        DIAG_COPYBOOK_FILE_COUNT_TEMPLATE.format(count=len(copybook_files))
    )
    logger.info(LOG_COPYBOOK_FILE_COUNT, len(copybook_files))

    for index, path in enumerate(copybook_files, start=1):
        text = file_loader.read_uploaded_text(LocalUploadedFile(path))
        text_parts.append(text)
        diagnostics.append(DIAG_COPYBOOK_FILE_TEMPLATE.format(index=index, path=path))
        diagnostics.append(
            DIAG_COPYBOOK_TEXT_LEN_TEMPLATE.format(index=index, length=len(text))
        )
        logger.info(LOG_COPYBOOK_FILE, index, path)
        logger.info(LOG_COPYBOOK_TEXT_LEN, index, len(text))

    copybook_text = "\n".join(text_parts)

    if copybook_text.strip():
        try:
            copybook_fields = copybook_parser.parse(
                text=copybook_text,
                source_label=COPYBOOK_SOURCE_LABEL,
            )
        except TypeError:
            copybook_fields = copybook_parser.parse(copybook_text)
    else:
        copybook_fields = []

    diagnostics.append(
        DIAG_COPYBOOK_TOTAL_FIELDS_TEMPLATE.format(count=len(copybook_fields))
    )
    logger.info(LOG_COPYBOOK_TOTAL_FIELDS, len(copybook_fields))

    if hasattr(copybook_parser, "diagnostics"):
        diagnostics.extend(copybook_parser.diagnostics)

    return copybook_fields


def load_shared_inputs(logger) -> tuple[list, list, list, list[str]]:
    diagnostics: list[str] = []

    sheet_parser = SheetMappingParser()
    dclgen_parser = DclgenParser()
    copybook_parser = CopybookParser()
    file_loader = FileLoader()

    diagnostics.append(DIAG_START_LOAD_INPUTS)
    logger.info(DIAG_START_LOAD_INPUTS)

    sheet_rows = _load_mapping_rows(sheet_parser, diagnostics, logger)
    dclgen_columns = _load_dclgen_columns(
        dclgen_parser, file_loader, diagnostics, logger
    )
    copybook_fields = _load_copybook_fields(
        copybook_parser, file_loader, diagnostics, logger
    )

    return sheet_rows, dclgen_columns, copybook_fields, diagnostics