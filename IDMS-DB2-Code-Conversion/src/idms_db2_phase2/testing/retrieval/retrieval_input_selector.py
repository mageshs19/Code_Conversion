from __future__ import annotations

from pathlib import Path

from config.path_settings import (
    DEFAULT_COPYBOOK_CANDIDATE_PATHS,
    DEFAULT_DCLGEN_CANDIDATE_PATHS,
    DEFAULT_MAPPING_SHEET_DIR,
    DEFAULT_RETRIEVAL_PROGRAM_DIR,
    DEFAULT_RETRIEVAL_SOURCE_PATH,
    DEFAULT_SHEET_MAPPING_PATH,
    copybook_paths,
    dclgen_paths,
    ensure_output_dirs,
    mapping_sheet_paths,
    retrieval_program_paths,
)
from rules.retrieval_runner_messages import (
    FILE_NOT_FOUND_TEMPLATE,
    FOLDER_NOT_FOUND_TEMPLATE,
    LABEL_MAPPING_SHEET,
    LABEL_RETRIEVAL_PROGRAM,
    LABEL_RETRIEVAL_PROGRAM_TEMPLATE,
    LABEL_SHEET_MAPPING,
    LABEL_COPYBOOK_TEMPLATE,
    LABEL_DCLGEN_TEMPLATE,
    NO_DCLGEN_CANDIDATE_TEMPLATE,
    NO_MAPPING_FILE_TEMPLATE,
    NO_PROGRAM_FILE_TEMPLATE,
    PATH_NOT_FILE_TEMPLATE,
    PATH_NOT_FOLDER_TEMPLATE,
)


def validate_file_exists(file_path: Path, label: str) -> None:
    if not file_path.exists():
        raise FileNotFoundError(
            FILE_NOT_FOUND_TEMPLATE.format(label=label, path=file_path)
        )
    if not file_path.is_file():
        raise FileNotFoundError(
            PATH_NOT_FILE_TEMPLATE.format(label=label, path=file_path)
        )


def validate_folder_exists(folder_path: Path, label: str) -> None:
    if not folder_path.exists():
        raise FileNotFoundError(
            FOLDER_NOT_FOUND_TEMPLATE.format(label=label, path=folder_path)
        )
    if not folder_path.is_dir():
        raise FileNotFoundError(
            PATH_NOT_FOLDER_TEMPLATE.format(label=label, path=folder_path)
        )


def selected_mapping_sheet_path() -> Path:
    mapping_paths = mapping_sheet_paths()

    if not mapping_paths and DEFAULT_SHEET_MAPPING_PATH.exists():
        return DEFAULT_SHEET_MAPPING_PATH

    if not mapping_paths:
        raise FileNotFoundError(
            NO_MAPPING_FILE_TEMPLATE.format(folder=DEFAULT_MAPPING_SHEET_DIR)
        )

    return mapping_paths[0]


def selected_dclgen_paths() -> list[Path]:
    paths = dclgen_paths()
    if paths:
        return paths
    return [
        path
        for path in DEFAULT_DCLGEN_CANDIDATE_PATHS
        if path.exists() and path.is_file()
    ]


def selected_copybook_paths() -> list[Path]:
    paths = copybook_paths()
    if paths:
        return paths
    return [
        path
        for path in DEFAULT_COPYBOOK_CANDIDATE_PATHS
        if path.exists() and path.is_file()
    ]


def selected_program_paths() -> list[Path]:
    paths = retrieval_program_paths()
    if paths:
        return paths

    if (
        DEFAULT_RETRIEVAL_SOURCE_PATH.exists()
        and DEFAULT_RETRIEVAL_SOURCE_PATH.is_file()
    ):
        return [DEFAULT_RETRIEVAL_SOURCE_PATH]

    return []


def validate_inputs() -> None:
    validate_folder_exists(DEFAULT_MAPPING_SHEET_DIR, LABEL_MAPPING_SHEET)
    validate_folder_exists(DEFAULT_RETRIEVAL_PROGRAM_DIR, LABEL_RETRIEVAL_PROGRAM)

    validate_file_exists(selected_mapping_sheet_path(), LABEL_SHEET_MAPPING)

    dclgen_files = selected_dclgen_paths()
    if not dclgen_files:
        searched = "\n".join(str(path) for path in DEFAULT_DCLGEN_CANDIDATE_PATHS)
        raise ValueError(NO_DCLGEN_CANDIDATE_TEMPLATE.format(searched=searched))

    for index, dclgen_path in enumerate(dclgen_files, start=1):
        validate_file_exists(
            dclgen_path,
            LABEL_DCLGEN_TEMPLATE.format(index=index),
        )

    for index, copybook_path in enumerate(selected_copybook_paths(), start=1):
        validate_file_exists(
            copybook_path,
            LABEL_COPYBOOK_TEMPLATE.format(index=index),
        )

    program_files = selected_program_paths()
    if not program_files:
        raise FileNotFoundError(
            NO_PROGRAM_FILE_TEMPLATE.format(folder=DEFAULT_RETRIEVAL_PROGRAM_DIR)
        )

    for index, program_path in enumerate(program_files, start=1):
        validate_file_exists(
            program_path,
            LABEL_RETRIEVAL_PROGRAM_TEMPLATE.format(index=index),
        )

    ensure_output_dirs()