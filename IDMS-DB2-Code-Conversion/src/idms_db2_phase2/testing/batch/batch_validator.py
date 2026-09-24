# LOCATION: src/idms_db2_phase2/testing/batch/batch_validator.py
# ACTION: REPLACE ENTIRE FILE
"""Batch input validation.

Mapping Sheet, DCLGen and Copybook folders are mandatory and raise.
The LRF folder is OPTIONAL metadata: a missing folder is created silently
and never blocks a batch, because programs that do not use COPY IDMS LR
convert exactly as before.
"""

from __future__ import annotations

from pathlib import Path

from config.path_settings import (
    DEFAULT_COPYBOOK_DIR,
    DEFAULT_DCLGEN_DIR,
    DEFAULT_LRF_DIR,
    DEFAULT_MAPPING_SHEET_DIR,
    ensure_lrf_dir,
    ensure_output_dirs,
    lrf_paths,
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
from rules.lrf_rules import LABEL_LRF

from .batch_models import BatchMode


# ------------------------------------------------------------ folders
def validate_folder(folder: Path, label: str) -> None:
    """Mandatory folder. Missing or not-a-folder is a hard stop."""
    if not folder.exists():
        raise FileNotFoundError(
            FOLDER_NOT_FOUND_TEMPLATE.format(label=label, folder=folder)
        )
    if not folder.is_dir():
        raise FileNotFoundError(
            PATH_NOT_FOLDER_TEMPLATE.format(label=label, folder=folder)
        )


def optional_folder(folder: Path) -> bool:
    """Optional folder. Returns True only when it exists and is a folder."""
    return folder.exists() and folder.is_dir()


def lrf_folder_status() -> tuple[bool, int]:
    """(folder_present, file_count) for the optional LRF input.

    Never raises. Callers use this only to narrate the batch report.
    """
    if not optional_folder(DEFAULT_LRF_DIR):
        return False, 0
    return True, len(lrf_paths())


def validate_common_input_folders() -> None:
    validate_folder(DEFAULT_MAPPING_SHEET_DIR, LABEL_MAPPING_SHEET)
    validate_folder(DEFAULT_DCLGEN_DIR, LABEL_DCLGEN)
    validate_folder(DEFAULT_COPYBOOK_DIR, LABEL_COPYBOOK)

    # ---- LRF is optional metadata, not a blocker.
    # Create it once so the folder always exists and the operator can see
    # where the subschema source is expected to be dropped.
    if not optional_folder(DEFAULT_LRF_DIR):
        ensure_lrf_dir()

    ensure_output_dirs()


def validate_mapping_files() -> None:
    """At least one mapping sheet must exist in the mapping folder."""
    if not mapping_sheet_paths():
        raise FileNotFoundError(
            NO_MAPPING_FILES_TEMPLATE.format(folder=DEFAULT_MAPPING_SHEET_DIR)
        )


# -------------------------------------------------------------- modes
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


__all__ = [
    "validate_folder",
    "optional_folder",
    "lrf_folder_status",
    "validate_common_input_folders",
    "validate_mapping_files",
    "program_paths_for_mode",
    "validate_mode",
    "LABEL_LRF",
]