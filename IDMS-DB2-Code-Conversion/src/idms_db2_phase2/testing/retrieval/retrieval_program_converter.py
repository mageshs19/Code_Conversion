# LOCATION: src/idms_db2_phase2/testing/retrieval/retrieval_program_converter.py
# ACTION: REPLACE ENTIRE FILE

"""Converts one retrieval program and prints its report.

CORRECTION - LRF metadata was never supplied
---------------------------------------------
`ConversionInput` carries a `logical_records` field. This runner never
populated it, so `LrfRepository` was always empty, `LrfPathExpander`
returned the source unchanged, and every program using COPY IDMS LR
shipped with raw LRF syntax:

    OBTAIN FIRST VMBTL03-R01 WHERE SWEEP-VMBFAS.

No expansion means no `OBTAIN ... WITHIN ...`, which means no cursor,
no OPEN/FETCH/CLOSE paragraphs and no SQLERROR anchor. The failure was
silent because LRF is optional by design.

The records are now loaded from the configured LRF folder when the
caller does not supply them, so run_retrieval.py needs no change.

READING
-------
The subschema is read with utf-8-sig, which transparently strips a UTF-8
byte order mark. A BOM left in the file makes the first token of
`ADD SUBSCHEMA ...` unmatchable and yields zero logical records with no
error at all.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from config.path_settings import DEFAULT_LRF_DIR, lrf_paths
from idms_db2_phase2.domain.models import ConversionInput
from idms_db2_phase2.infrastructure.file_loader import FileLoader
from idms_db2_phase2.infrastructure.local_uploaded_file import LocalUploadedFile
from idms_db2_phase2.orchestration.conversion_service import ConversionService
from idms_db2_phase2.parsers.cobol_parser import CobolParser
from idms_db2_phase2.parsers.lrf_parser import LrfParser
from idms_db2_phase2.services.name_derivation_resolver import NameDerivationResolver
from patterns.lrf_patterns import COPY_IDMS_LR_PATTERN
from rules.lrf_rules import (
    DIAG_LRF_FILE_COUNT_TEMPLATE,
    DIAG_LRF_FILE_TEMPLATE,
    DIAG_LRF_FOLDER_TEMPLATE,
    DIAG_LRF_NO_RECORDS_IN_SCOPE,
    DIAG_LRF_PARSED_ZERO,
    DIAG_LRF_PARSE_FAILED_TEMPLATE,
    DIAG_LRF_READ_FAILED_TEMPLATE,
    DIAG_LRF_RECORDS_IN_SCOPE_TEMPLATE,
    DIAG_LRF_TEXT_LEN_TEMPLATE,
    DIAG_LRF_TOTAL_RECORDS_TEMPLATE,
    LABEL_LRF,
    LOG_LRF_FILE_COUNT,
    LOG_LRF_TOTAL_RECORDS,
    LRF_VALIDATION_MESSAGES,
)
from rules.retrieval_runner_messages import (
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
from rules.retrieval_runner_rules import (
    AUTO_FIX_PIC_LENGTH_MISMATCHES_DEFAULT,
    COBOL_TEXT_ENCODING,
    OUTPUT_FILE_EXTENSION,
    OUTPUT_FILE_NAME_TEMPLATE,
    OUTPUT_TIMESTAMP_FORMAT,
)

from .retrieval_input_selector import (
    selected_copybook_paths,
    selected_dclgen_paths,
    selected_mapping_sheet_path,
)

# Reading with utf-8-sig strips a leading byte order mark transparently.
LRF_TEXT_ENCODING = "utf-8-sig"
LRF_SOURCE_LABEL = "LRF files"


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


#
# LRF (Logical Record Facility)
#
def _read_lrf_text(path: Path, file_loader: FileLoader) -> str:
    """Read one subschema, BOM tolerant.

    FileLoader is tried first so behaviour matches the Streamlit upload
    path. A direct utf-8-sig read is the fallback, because a BOM left in
    the file silently produces zero logical records.
    """
    try:
        text = file_loader.read_uploaded_text(LocalUploadedFile(path))
        if str(text or "").strip():
            return str(text).lstrip("\ufeff")
    except Exception:  # noqa: BLE001
        pass

    return Path(path).read_text(
        encoding=LRF_TEXT_ENCODING,
        errors="replace",
    )


def _parse_lrf_text(parser: LrfParser, text: str) -> list:
    """Parse subschema text, tolerating either parse() signature."""
    try:
        return list(parser.parse(text, source_label=LRF_SOURCE_LABEL) or [])
    except TypeError:
        return list(parser.parse(text) or [])


def load_logical_records(diagnostics: list[str], logger) -> list:
    """Every logical record declared in the configured LRF folder.

    Never raises and never blocks a run: LRF is optional metadata. A
    folder that is missing, empty or unreadable yields an empty list and
    a diagnostic, exactly as the batch loader does.
    """
    diagnostics.append(DIAG_LRF_FOLDER_TEMPLATE.format(folder=DEFAULT_LRF_DIR))

    try:
        files = [Path(path) for path in (lrf_paths() or [])]
    except Exception as exc:  # noqa: BLE001
        diagnostics.append(
            DIAG_LRF_READ_FAILED_TEMPLATE.format(
                name=DEFAULT_LRF_DIR,
                reason=exc,
            )
        )
        files = []

    diagnostics.append(DIAG_LRF_FILE_COUNT_TEMPLATE.format(count=len(files)))
    logger.info(LOG_LRF_FILE_COUNT, len(files))

    if not files:
        diagnostics.append(DIAG_LRF_PARSED_ZERO)
        return []

    file_loader = FileLoader()
    parser = LrfParser()
    text_parts: list[str] = []

    for index, path in enumerate(files, start=1):
        diagnostics.append(
            DIAG_LRF_FILE_TEMPLATE.format(index=index, path=path)
        )

        try:
            text = _read_lrf_text(path, file_loader)
        except Exception as exc:  # noqa: BLE001
            diagnostics.append(
                DIAG_LRF_READ_FAILED_TEMPLATE.format(name=path, reason=exc)
            )
            continue

        diagnostics.append(
            DIAG_LRF_TEXT_LEN_TEMPLATE.format(index=index, length=len(text))
        )
        text_parts.append(text)

    combined = "\n".join(text_parts)

    if not combined.strip():
        diagnostics.append(DIAG_LRF_PARSED_ZERO)
        return []

    try:
        records = _parse_lrf_text(parser, combined)
    except Exception as exc:  # noqa: BLE001
        diagnostics.append(
            DIAG_LRF_PARSE_FAILED_TEMPLATE.format(
                name=LRF_SOURCE_LABEL,
                reason=exc,
            )
        )
        return []

    diagnostics.append(
        DIAG_LRF_TOTAL_RECORDS_TEMPLATE.format(count=len(records))
    )
    logger.info(LOG_LRF_TOTAL_RECORDS, len(records))

    parser_diagnostics = getattr(parser, "diagnostics", None)
    if parser_diagnostics:
        diagnostics.extend(str(item) for item in parser_diagnostics)

    return records


def _source_uses_logical_records(source_text: str) -> list[str]:
    """Logical record names the SOURCE copies via COPY IDMS LR."""
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
    """Record what LRF metadata this program run will actually see.

    A program that copies a logical record without a matching subschema
    is reported once, so the gap is visible in the run log instead of
    failing silently.
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

    used = _source_uses_logical_records(source_text)

    if used and not logical_records:
        message = LRF_VALIDATION_MESSAGES["missing_lrf"]
        diagnostics.append(message)
        logger.warning(message)


#
# Reporting
#
def _print_summary(
    *,
    program_path,
    sheet_rows,
    dclgen_columns,
    copybook_fields,
    logical_records,
    idms_len,
    target_program_id,
    project_root,
    src_dir,
):
    print("")
    print(HEADER_INPUT_SUMMARY)
    print(RULE_INPUT_SUMMARY)
    print(SUMMARY_PROJECT_ROOT_TEMPLATE.format(value=project_root))
    print(SUMMARY_SRC_DIR_TEMPLATE.format(value=src_dir))
    print(SUMMARY_SHEET_ROWS_TEMPLATE.format(value=len(sheet_rows)))
    print(SUMMARY_DCLGEN_COLUMNS_TEMPLATE.format(value=len(dclgen_columns)))
    print(SUMMARY_COPYBOOK_FIELDS_TEMPLATE.format(value=len(copybook_fields)))
    print(f"{LABEL_LRF} Records : {len(logical_records)}")
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

    try:
        lrf_files = list(lrf_paths() or [])
    except Exception:  # noqa: BLE001
        lrf_files = []

    print(f"{LABEL_LRF} Files:")
    if lrf_files:
        for path in lrf_files:
            print(SELECTED_PATH_BULLET_TEMPLATE.format(value=path))
    else:
        print(SELECTED_PATH_BULLET_TEMPLATE.format(value="None"))


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


#
# Public entry point
#
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
    logical_records: list | None = None,
) -> Path:
    """Convert one retrieval program.

    `logical_records` is OPTIONAL. When the caller does not supply it the
    configured LRF folder is read here, so run_retrieval.py works with no
    change while a batch caller can still load the subschema once and
    share it across every program.
    """
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

    # LRF sits between Copybook metadata and the COBOL source.
    records = (
        list(logical_records)
        if logical_records is not None
        else load_logical_records(diagnostics, logger)
    )

    _narrate_lrf(
        source_text=idms_cobol_text,
        logical_records=records,
        diagnostics=diagnostics,
        logger=logger,
    )

    result = ConversionService().convert(
        ConversionInput(
            sheet_mapping_rows=sheet_rows,
            dclgen_columns=dclgen_columns,
            copybook_fields=copybook_fields,
            logical_records=records,
            idms_cobol_text=idms_cobol_text,
            target_program_id=target_program_id,
            auto_fix_pic_length_mismatches=AUTO_FIX_PIC_LENGTH_MISMATCHES_DEFAULT,
        )
    )

    output_cobol_path = _build_output_path(output_dir, program_path)
    output_cobol_path.write_text(
        result.converted_cobol or "",
        encoding=COBOL_TEXT_ENCODING,
    )

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
        logical_records=records,
        idms_len=len(idms_cobol_text),
        target_program_id=target_program_id,
        project_root=project_root,
        src_dir=src_dir,
    )
    _print_results(result, diagnostics, logger)

    return output_cobol_path


__all__ = [
    "convert_one_program",
    "load_logical_records",
    "resolve_target_program_id",
]