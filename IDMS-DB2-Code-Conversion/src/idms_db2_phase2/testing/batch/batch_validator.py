from __future__ import annotations

from pathlib import Path

from config.path_settings import (
    DEFAULT_COPYBOOK_DIR,
    DEFAULT_DCLGEN_DIR,
    DEFAULT_MAPPING_SHEET_DIR,
    ensure_output_dirs,
    mapping_sheet_paths,
    retrieval_program_paths,
    update_program_paths,
)
from rules.batch_runner_messages import (
    FOLDER_NOT_FOUND_TEMPLATE,
    LABEL_COPYBOOK,
    LABEL_DCLGEN,
    LABEL_MAPPING_SHEET,
    LABEL_PROGRAM_TEMPLATE,
    NO_MAPPING_FILES_TEMPLATE,
    NO_PROGRAM_FILES_TEMPLATE,
    PATH_NOT_FOLDER_TEMPLATE,
    UNSUPPORTED_MODE_TEMPLATE,
)
from rules.batch_runner_rules import BATCH_MODE_RETRIEVAL, BATCH_MODE_UPDATE

from .batch_models import BatchMode


def validate_folder(folder: Path, label: str) -> None:
    if not folder.exists():
        raise FileNotFoundError(
            FOLDER_NOT_FOUND_TEMPLATE.format(label=label, folder=folder)
        )
    if not folder.is_dir():
        raise FileNotFoundError(
            PATH_NOT_FOLDER_TEMPLATE.format(label=label, folder=folder)
        )


def validate_common_input_folders() -> None:
    validate_folder(DEFAULT_MAPPING_SHEET_DIR, LABEL_MAPPING_SHEET)
    validate_folder(DEFAULT_DCLGEN_DIR, LABEL_DCLGEN)
    validate_folder(DEFAULT_COPYBOOK_DIR, LABEL_COPYBOOK)
    ensure_output_dirs()


def program_paths_for_mode(mode_name: str) -> list[Path]:
    normalized = str(mode_name or "").strip().upper()

    if normalized == BATCH_MODE_UPDATE:
        return update_program_paths()

    if normalized == BATCH_MODE_RETRIEVAL:
        return retrieval_program_paths()

    raise ValueError(UNSUPPORTED_MODE_TEMPLATE.format(mode=mode_name))


def validate_mode(mode: BatchMode) -> None:
    validate_folder(
        mode.program_dir,
        LABEL_PROGRAM_TEMPLATE.format(mode=mode.name),
    )
    mode.output_dir.mkdir(parents=True, exist_ok=True)

    programs = program_paths_for_mode(mode.name)
    if not programs:
        raise FileNotFoundError(
            NO_PROGRAM_FILES_TEMPLATE.format(
                mode=mode.name,
                folder=mode.program_dir,
            )
        )

    mapping_files = mapping_sheet_paths()
    if not mapping_files:
        raise FileNotFoundError(
            NO_MAPPING_FILES_TEMPLATE.format(folder=DEFAULT_MAPPING_SHEET_DIR)
        )