from __future__ import annotations

from config.path_settings import (
    DEFAULT_COPYBOOK_DIR,
    DEFAULT_DCLGEN_DIR,
    DEFAULT_MAPPING_SHEET_DIR,
    copybook_paths,
    dclgen_paths,
    mapping_sheet_paths,
)
from idms_db2_phase2.infrastructure.file_loader import FileLoader
from idms_db2_phase2.infrastructure.local_uploaded_file import LocalUploadedFile
from idms_db2_phase2.parsers.copybook_parser import CopybookParser
from idms_db2_phase2.parsers.dclgen_parser import DclgenParser
from idms_db2_phase2.parsers.sheet_mapping_parser import SheetMappingParser
from rules.batch_runner_messages import (
    COPYBOOK_SOURCE_LABEL,
    DCLGEN_SOURCE_LABEL_TEMPLATE,
    DIAG_COPYBOOK_FILE_COUNT_TEMPLATE,
    DIAG_COPYBOOK_FILE_TEMPLATE,
    DIAG_COPYBOOK_FOLDER_TEMPLATE,
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
    DIAG_MULTIPLE_MAPPING_TEMPLATE,
    DIAG_START_LOAD_SHARED_INPUTS,
    NO_DCLGEN_FILES_TEMPLATE,
    NO_MAPPING_IN_FOLDER_TEMPLATE,
)

from .batch_models import SharedInputs


def _load_mapping_rows(sheet_parser, diagnostics: list[str]):
    mapping_files = mapping_sheet_paths()
    if not mapping_files:
        raise FileNotFoundError(
            NO_MAPPING_IN_FOLDER_TEMPLATE.format(folder=DEFAULT_MAPPING_SHEET_DIR)
        )

    if len(mapping_files) > 1:
        names = ", ".join(path.name for path in mapping_files)
        diagnostics.append(
            DIAG_MULTIPLE_MAPPING_TEMPLATE.format(
                first=mapping_files[0].name,
                names=names,
            )
        )

    sheet_path = mapping_files[0]
    sheet_rows = sheet_parser.parse_uploaded_file(LocalUploadedFile(sheet_path))

    diagnostics.append(
        DIAG_MAPPING_FOLDER_TEMPLATE.format(folder=DEFAULT_MAPPING_SHEET_DIR)
    )
    diagnostics.append(DIAG_MAPPING_SELECTED_TEMPLATE.format(path=sheet_path))
    diagnostics.append(DIAG_MAPPING_ROWS_TEMPLATE.format(count=len(sheet_rows)))

    if hasattr(sheet_parser, "diagnostics"):
        diagnostics.extend(sheet_parser.diagnostics)

    return sheet_rows


def _load_dclgen_columns(dclgen_parser, file_loader, diagnostics: list[str]):
    dclgen_files = dclgen_paths()
    diagnostics.append(DIAG_DCLGEN_FOLDER_TEMPLATE.format(folder=DEFAULT_DCLGEN_DIR))
    diagnostics.append(
        DIAG_DCLGEN_FILE_COUNT_TEMPLATE.format(count=len(dclgen_files))
    )

    if not dclgen_files:
        raise FileNotFoundError(
            NO_DCLGEN_FILES_TEMPLATE.format(folder=DEFAULT_DCLGEN_DIR)
        )

    dclgen_texts: list[str] = []
    for index, path in enumerate(dclgen_files, start=1):
        text = file_loader.read_uploaded_text(LocalUploadedFile(path))
        dclgen_texts.append(text)
        diagnostics.append(DIAG_DCLGEN_FILE_TEMPLATE.format(index=index, path=path))
        diagnostics.append(
            DIAG_DCLGEN_TEXT_LEN_TEMPLATE.format(index=index, length=len(text))
        )

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
    if hasattr(dclgen_parser, "diagnostics"):
        diagnostics.extend(dclgen_parser.diagnostics)

    return dclgen_columns


def _load_copybook_fields(copybook_parser, file_loader, diagnostics: list[str]):
    copybook_files = copybook_paths()
    text_parts: list[str] = []

    diagnostics.append(
        DIAG_COPYBOOK_FOLDER_TEMPLATE.format(folder=DEFAULT_COPYBOOK_DIR)
    )
    diagnostics.append(
        DIAG_COPYBOOK_FILE_COUNT_TEMPLATE.format(count=len(copybook_files))
    )

    for index, path in enumerate(copybook_files, start=1):
        text = file_loader.read_uploaded_text(LocalUploadedFile(path))
        text_parts.append(text)
        diagnostics.append(
            DIAG_COPYBOOK_FILE_TEMPLATE.format(index=index, path=path)
        )
        diagnostics.append(
            DIAG_COPYBOOK_TEXT_LEN_TEMPLATE.format(index=index, length=len(text))
        )

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
    if hasattr(copybook_parser, "diagnostics"):
        diagnostics.extend(copybook_parser.diagnostics)

    return copybook_fields


def load_shared_inputs(logger) -> SharedInputs:
    diagnostics: list[str] = []

    sheet_parser = SheetMappingParser()
    dclgen_parser = DclgenParser()
    copybook_parser = CopybookParser()
    file_loader = FileLoader()

    diagnostics.append(DIAG_START_LOAD_SHARED_INPUTS)
    logger.info(DIAG_START_LOAD_SHARED_INPUTS)

    sheet_rows = _load_mapping_rows(sheet_parser, diagnostics)
    dclgen_columns = _load_dclgen_columns(dclgen_parser, file_loader, diagnostics)
    copybook_fields = _load_copybook_fields(copybook_parser, file_loader, diagnostics)

    return SharedInputs(
        sheet_rows=sheet_rows,
        dclgen_columns=dclgen_columns,
        copybook_fields=copybook_fields,
        diagnostics=diagnostics,
    )