from __future__ import annotations

import streamlit as st

from idms_db2_phase2.infrastructure.file_loader import FileLoader
from idms_db2_phase2.parsers.copybook_parser import CopybookParser
from idms_db2_phase2.parsers.dclgen_parser import DclgenParser
from idms_db2_phase2.parsers.sheet_mapping_parser import SheetMappingParser
from idms_db2_phase2.ui.session_state import reset_generated_output_state


def load_and_analyze_inputs(
    sheet_mapping_file,
    dclgen_files,
    copybook_files,
    idms_cobol_source_file,
) -> None:
    diagnostics: list[str] = []
    uploaded_file_names: dict[str, object] = {}

    file_loader = FileLoader()
    sheet_mapping_parser = SheetMappingParser()
    dclgen_parser = DclgenParser()
    copybook_parser = CopybookParser()

    diagnostics.append("START LOAD INPUTS")

    sheet_rows = _load_sheet_mapping(
        sheet_mapping_file=sheet_mapping_file,
        parser=sheet_mapping_parser,
        diagnostics=diagnostics,
        uploaded_file_names=uploaded_file_names,
    )

    dclgen_columns = _load_dclgen_files(
        dclgen_files=dclgen_files,
        file_loader=file_loader,
        parser=dclgen_parser,
        diagnostics=diagnostics,
        uploaded_file_names=uploaded_file_names,
    )

    copybook_fields = _load_copybook_files(
        copybook_files=copybook_files,
        file_loader=file_loader,
        parser=copybook_parser,
        diagnostics=diagnostics,
        uploaded_file_names=uploaded_file_names,
    )

    idms_cobol_text, idms_cobol_source_name = _load_idms_cobol_source(
        idms_cobol_source_file=idms_cobol_source_file,
        file_loader=file_loader,
        diagnostics=diagnostics,
        uploaded_file_names=uploaded_file_names,
    )

    st.session_state.sheet_mapping_rows = sheet_rows
    st.session_state.dclgen_columns = dclgen_columns
    st.session_state.copybook_fields = copybook_fields
    st.session_state.idms_cobol_text = idms_cobol_text
    st.session_state.idms_cobol_source_name = idms_cobol_source_name

    reset_generated_output_state()

    st.session_state.diagnostics = diagnostics
    st.session_state.uploaded_file_names = uploaded_file_names

    required_inputs_loaded = (
        bool(sheet_rows)
        and bool(dclgen_columns)
        and bool(idms_cobol_text.strip())
    )

    st.session_state.loaded = required_inputs_loaded

    if required_inputs_loaded:
        st.success("Inputs loaded and analyzed.")
    else:
        st.warning(
            "Inputs were processed, but one or more required inputs are missing "
            "or parsed as empty. Review the Diagnostics tab."
        )


def _load_sheet_mapping(
    *,
    sheet_mapping_file,
    parser: SheetMappingParser,
    diagnostics: list[str],
    uploaded_file_names: dict[str, object],
) -> list:
    if sheet_mapping_file is None:
        diagnostics.append("Sheet Mapping file not uploaded.")
        return []

    uploaded_file_names["sheet_mapping_file"] = str(sheet_mapping_file.name or "")

    try:
        rows = parser.parse_uploaded_file(sheet_mapping_file)
        diagnostics.append(f"Sheet Mapping uploaded: {sheet_mapping_file.name}")
        diagnostics.append(f"Sheet Mapping parsed rows: {len(rows)}")

        if hasattr(parser, "diagnostics"):
            diagnostics.extend(parser.diagnostics)

        return rows

    except Exception as exc:
        diagnostics.append(f"Sheet Mapping parse failed: {exc}")
        return []


def _load_dclgen_files(
    *,
    dclgen_files,
    file_loader: FileLoader,
    parser: DclgenParser,
    diagnostics: list[str],
    uploaded_file_names: dict[str, object],
) -> list:
    if not dclgen_files:
        diagnostics.append("DCLGEN file not uploaded.")
        return []

    diagnostics.append(f"DCLGEN file count: {len(dclgen_files)}")

    file_names: list[str] = []
    texts: list[str] = []

    for index, file in enumerate(dclgen_files, start=1):
        file_name = str(file.name or "")
        file_names.append(file_name)

        try:
            text = file_loader.read_uploaded_text(file)
            texts.append(text)
            diagnostics.append(f"DCLGEN {index}: {file_name}")
            diagnostics.append(f"DCLGEN {index} text length: {len(text)}")

        except Exception as exc:
            diagnostics.append(f"DCLGEN read failed for {file_name}: {exc}")

    uploaded_file_names["dclgen_files"] = file_names

    try:
        if hasattr(parser, "parse_many_texts"):
            columns = parser.parse_many_texts(texts)
        else:
            columns = []

            for index, text in enumerate(texts, start=1):
                parsed_columns = parser.parse(
                    text=text,
                    source_label=f"DCLGEN file {index}",
                )
                columns.extend(parsed_columns)

        diagnostics.append(f"DCLGEN parsed columns: {len(columns)}")

        if hasattr(parser, "diagnostics"):
            diagnostics.extend(parser.diagnostics)

        return columns

    except Exception as exc:
        diagnostics.append(f"DCLGEN parse failed: {exc}")
        return []


def _load_copybook_files(
    *,
    copybook_files,
    file_loader: FileLoader,
    parser: CopybookParser,
    diagnostics: list[str],
    uploaded_file_names: dict[str, object],
) -> list:
    if not copybook_files:
        diagnostics.append("Copybook file not uploaded. Continuing without copybook.")
        return []

    diagnostics.append(f"Copybook file count: {len(copybook_files)}")

    file_names: list[str] = []
    text_parts: list[str] = []

    for index, file in enumerate(copybook_files, start=1):
        file_name = str(file.name or "")
        file_names.append(file_name)

        try:
            text = file_loader.read_uploaded_text(file)
            text_parts.append(text)
            diagnostics.append(f"Copybook {index}: {file_name}")
            diagnostics.append(f"Copybook {index} text length: {len(text)}")

        except Exception as exc:
            diagnostics.append(f"Copybook read failed for {file_name}: {exc}")

    uploaded_file_names["copybook_files"] = file_names

    copybook_text = "\n".join(text_parts)

    if not copybook_text.strip():
        diagnostics.append("Copybook parsed fields: 0")
        return []

    try:
        try:
            fields = parser.parse(
                text=copybook_text,
                source_label="Copybook files",
            )
        except TypeError:
            fields = parser.parse(copybook_text)

        diagnostics.append(f"Copybook parsed fields: {len(fields)}")

        if hasattr(parser, "diagnostics"):
            diagnostics.extend(parser.diagnostics)

        return fields

    except Exception as exc:
        diagnostics.append(f"Copybook parse failed: {exc}")
        diagnostics.append("Copybook parsed fields: 0")
        return []


def _load_idms_cobol_source(
    *,
    idms_cobol_source_file,
    file_loader: FileLoader,
    diagnostics: list[str],
    uploaded_file_names: dict[str, object],
) -> tuple[str, str]:
    if idms_cobol_source_file is None:
        diagnostics.append("IDMS COBOL source file not uploaded.")
        return "", ""

    source_name = str(idms_cobol_source_file.name or "")
    uploaded_file_names["idms_cobol_source_file"] = source_name

    try:
        text = file_loader.read_uploaded_text(idms_cobol_source_file)
        diagnostics.append(f"IDMS COBOL source uploaded: {source_name}")
        diagnostics.append(f"IDMS COBOL source text length: {len(text)}")
        return text, source_name

    except Exception as exc:
        diagnostics.append(f"IDMS COBOL source read failed: {exc}")
        return "", source_name