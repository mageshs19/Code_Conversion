r"""
Path settings for local command-line runs.

These paths are intentionally centralized here instead of being embedded in
runner, parser, transformer, generator, or orchestration logic.

Folder-based local input layout:

C:\S\S-Input
  Mapping Sheet
    Excel_Sheet_mapping.csv
  DCLGen
    *.txt / *.cbl / *.cob / *.cpy
  Copybook
    *.txt / *.cbl / *.cob / *.cpy
  Program
    Retrieval
      *.txt / *.cbl / *.cob
    Update
      *.txt / *.cbl / *.cob
  Output
    Retrieval
    Update
"""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
LOGS_DIR = PROJECT_ROOT / "logs"

DEFAULT_INPUT_DIR = Path(r"C:\S\S-Input")

DEFAULT_MAPPING_SHEET_DIR = DEFAULT_INPUT_DIR / "Mapping Sheet"
DEFAULT_DCLGEN_DIR = DEFAULT_INPUT_DIR / "DCLGen"
DEFAULT_COPYBOOK_DIR = DEFAULT_INPUT_DIR / "Copybook"
DEFAULT_PROGRAM_DIR = DEFAULT_INPUT_DIR / "Program"

DEFAULT_RETRIEVAL_PROGRAM_DIR = DEFAULT_PROGRAM_DIR / "Retrieval"
DEFAULT_UPDATE_PROGRAM_DIR = DEFAULT_PROGRAM_DIR / "Update"

DEFAULT_OUTPUT_DIR = DEFAULT_INPUT_DIR / "Output"
DEFAULT_RETRIEVAL_OUTPUT_DIR = DEFAULT_OUTPUT_DIR / "Retrieval"
DEFAULT_UPDATE_OUTPUT_DIR = DEFAULT_OUTPUT_DIR / "Update"

SUPPORTED_MAPPING_EXTENSIONS = (
    ".csv",
    ".xlsx",
)

SUPPORTED_TEXT_EXTENSIONS = (
    ".txt",
    ".cbl",
    ".cob",
    ".cpy",
)

DEFAULT_SHEET_MAPPING_PATH = DEFAULT_MAPPING_SHEET_DIR / "Excel_Sheet_mapping.csv"
DEFAULT_RETRIEVAL_SOURCE_PATH = DEFAULT_RETRIEVAL_PROGRAM_DIR / "Retrieval.txt"
DEFAULT_UPDATE_SOURCE_PATH = DEFAULT_UPDATE_PROGRAM_DIR / "Update.txt"


def existing_files(
    paths: list[Path],
) -> list[Path]:
    """
    Return only paths that exist and are files.
    """
    return [
        path
        for path in paths
        if path.exists() and path.is_file()
    ]


def files_in_folder(
    folder: Path,
    extensions: tuple[str, ...],
) -> list[Path]:
    """
    Return supported files from a folder in stable name order.
    """
    if not folder.exists() or not folder.is_dir():
        return []

    normalized_extensions = tuple(
        extension.lower()
        for extension in extensions
    )

    return sorted(
        [
            path
            for path in folder.iterdir()
            if path.is_file()
            and path.suffix.lower() in normalized_extensions
        ],
        key=lambda item: item.name.lower(),
    )


def mapping_sheet_paths() -> list[Path]:
    """
    Return mapping sheet files from the single mapping sheet folder.

    If Excel_Sheet_mapping.csv exists, it is preferred first.
    """
    paths = files_in_folder(
        DEFAULT_MAPPING_SHEET_DIR,
        SUPPORTED_MAPPING_EXTENSIONS,
    )

    if DEFAULT_SHEET_MAPPING_PATH.exists() and DEFAULT_SHEET_MAPPING_PATH.is_file():
        preferred = DEFAULT_SHEET_MAPPING_PATH
        paths = [
            preferred,
            *[
                path
                for path in paths
                if path.resolve() != preferred.resolve()
            ],
        ]

    return paths


def dclgen_paths() -> list[Path]:
    """
    Return all DCLGEN files from the DCLGen folder.
    """
    return files_in_folder(
        DEFAULT_DCLGEN_DIR,
        SUPPORTED_TEXT_EXTENSIONS,
    )


def copybook_paths() -> list[Path]:
    """
    Return all copybook files from the Copybook folder.
    """
    return files_in_folder(
        DEFAULT_COPYBOOK_DIR,
        SUPPORTED_TEXT_EXTENSIONS,
    )


def retrieval_program_paths() -> list[Path]:
    """
    Return all retrieval COBOL program files.
    """
    return files_in_folder(
        DEFAULT_RETRIEVAL_PROGRAM_DIR,
        SUPPORTED_TEXT_EXTENSIONS,
    )


def update_program_paths() -> list[Path]:
    """
    Return all update COBOL program files.
    """
    return files_in_folder(
        DEFAULT_UPDATE_PROGRAM_DIR,
        SUPPORTED_TEXT_EXTENSIONS,
    )


def ensure_output_dirs() -> None:
    """
    Ensure output folders exist.
    """
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_RETRIEVAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_UPDATE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


DEFAULT_DCLGEN_CANDIDATE_PATHS = dclgen_paths()
DEFAULT_COPYBOOK_CANDIDATE_PATHS = copybook_paths()