
# LOCATION: config/path_settings.py
# ACTION: REPLACE ENTIRE FILE
r"""Path settings for local command-line runs.

These paths are intentionally centralized here instead of being embedded in
runner, parser, or conversion logic.

TWO SUPPORTED LAYOUTS
=====================

KIND layout (legacy local workbench)      FLAT layout (Zowe workspace)
------------------------------------      ----------------------------
<root>\Mapping Sheet\Retrieval\           <root>\Mapping Sheet\
<root>\Mapping Sheet\Update\              <root>\DCLGen\
<root>\DCLGen\                            <root>\Copybook\
<root>\Copybook\                          <root>\Program\
<root>\LRF\                               <root>\Subschema\
<root>\Program\Retrieval\                 <root>\Output\
<root>\Program\Update\
<root>\Output\Retrieval\
<root>\Output\Update\

zowe/zowe_workspace.py states it plainly: "One Program folder. No Retrieval /
Update split." The converter is launched by the pipeline as a SUBPROCESS, so
the shape it must read is decided HERE, once, from the input root that the
parent published through IDMS_INPUT_DIR.

DECISION RULE
-------------
1. IDMS_LAYOUT=FLAT or IDMS_LAYOUT=KIND wins outright.
2. Otherwise KIND when Program\Retrieval or Program\Update EXISTS.
3. Otherwise FLAT.

Rule 2 tests EXISTENCE, not contents. A freshly created workspace has an
empty Program folder, and a contents test would send the converter to
Program\Retrieval, which Zowe never creates - that is exactly the
"nothing to convert on a folder that is full" defect.

Every public name below is unchanged, so run_retrieval.py, run_update.py,
retrieval_input_selector.py, update_input_selector.py, batch_validator.py,
shared_input_loader.py and review_retrieval.py import it as before.
"""

from __future__ import annotations

import os
from pathlib import Path


# ---------------------------------------------------------------- project
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
LOGS_DIR = PROJECT_ROOT / "logs"


# ------------------------------------------------------------- input root
# The Zowe pipeline publishes its workspace through this key. Without it
# the child process silently used the developer default.
INPUT_DIR_ENV_KEY = "IDMS_INPUT_DIR"
LAYOUT_ENV_KEY = "IDMS_LAYOUT"

LAYOUT_FLAT = "FLAT"
LAYOUT_KIND = "KIND"

# Local workbench default. Overridden by IDMS_INPUT_DIR in every pipeline run.
FALLBACK_INPUT_DIR = Path(
    r"H:\Belfius\IDMS-DB2\Input"
    r"\Case2-Automation on COBOL IDMS to COBOL DB2 - Code Conversion Phase"
)

FALLBACK_INPUT_DIR = Path(r"C:\S\S-Input")


def _input_root() -> Path:
    configured = os.environ.get(INPUT_DIR_ENV_KEY, "").strip().strip('"')
    return Path(configured) if configured else FALLBACK_INPUT_DIR


DEFAULT_INPUT_DIR = _input_root()


# --------------------------------------------------------- first-level dirs
DEFAULT_MAPPING_SHEET_DIR = DEFAULT_INPUT_DIR / "Mapping Sheet"
DEFAULT_DCLGEN_DIR = DEFAULT_INPUT_DIR / "DCLGen"
DEFAULT_COPYBOOK_DIR = DEFAULT_INPUT_DIR / "Copybook"
DEFAULT_PROGRAM_DIR = DEFAULT_INPUT_DIR / "Program"
DEFAULT_OUTPUT_DIR = DEFAULT_INPUT_DIR / "Output"

KIND_RETRIEVAL_FOLDER = "Retrieval"
KIND_UPDATE_FOLDER = "Update"


# --------------------------------------------------------------- layout
def _configured_layout() -> str:
    value = os.environ.get(LAYOUT_ENV_KEY, "").strip().upper()
    return value if value in (LAYOUT_FLAT, LAYOUT_KIND) else ""


def _detect_layout() -> str:
    """FLAT unless the legacy kind sub-folders actually exist."""
    configured = _configured_layout()
    if configured:
        return configured

    nested = (
        (DEFAULT_PROGRAM_DIR / KIND_RETRIEVAL_FOLDER).is_dir()
        or (DEFAULT_PROGRAM_DIR / KIND_UPDATE_FOLDER).is_dir()
    )
    return LAYOUT_KIND if nested else LAYOUT_FLAT


INPUT_LAYOUT = _detect_layout()
LAYOUT_IS_FLAT = INPUT_LAYOUT == LAYOUT_FLAT


def _kind_dir(parent: Path, kind: str) -> Path:
    """<parent> when flat, <parent>/<kind> when the split layout is in use."""
    return parent if LAYOUT_IS_FLAT else parent / kind


# ------------------------------------------------------- resolved folders
DEFAULT_RETRIEVAL_MAPPING_SHEET_DIR = _kind_dir(
    DEFAULT_MAPPING_SHEET_DIR, KIND_RETRIEVAL_FOLDER
)
DEFAULT_UPDATE_MAPPING_SHEET_DIR = _kind_dir(
    DEFAULT_MAPPING_SHEET_DIR, KIND_UPDATE_FOLDER
)

DEFAULT_RETRIEVAL_PROGRAM_DIR = _kind_dir(
    DEFAULT_PROGRAM_DIR, KIND_RETRIEVAL_FOLDER
)
DEFAULT_UPDATE_PROGRAM_DIR = _kind_dir(
    DEFAULT_PROGRAM_DIR, KIND_UPDATE_FOLDER
)

# Output MUST follow the same shape. The pipeline hands the review step
# --folder <root>\Output; writing to <root>\Output\Retrieval would leave
# review with nothing to do while convert reported OK.
DEFAULT_RETRIEVAL_OUTPUT_DIR = _kind_dir(
    DEFAULT_OUTPUT_DIR, KIND_RETRIEVAL_FOLDER
)
DEFAULT_UPDATE_OUTPUT_DIR = _kind_dir(
    DEFAULT_OUTPUT_DIR, KIND_UPDATE_FOLDER
)


# ------------------------------------------------------------ extensions
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

SUPPORTED_LRF_EXTENSIONS = (
    ".txt",
    ".sub",
    ".sch",
    ".cpy",
    ".cbl",
)


# --------------------------------------------------------- LRF subschema
# Local workbench drops the subschema in <root>\LRF. Zowe lands it in
# <root>\Subschema (see zowe_workspace.WORKSPACE_SUBFOLDERS). Both are
# read, LRF first, so a program using COPY IDMS LR expands in either mode.
DEFAULT_LRF_DIR = DEFAULT_INPUT_DIR / "LRF"
DEFAULT_SUBSCHEMA_DIR = DEFAULT_INPUT_DIR / "Subschema"


# ------------------------------------------------------- sentinel paths
DEFAULT_SHEET_MAPPING_PATH = DEFAULT_MAPPING_SHEET_DIR / "Excel_Sheet_mapping.csv"
DEFAULT_RETRIEVAL_SOURCE_PATH = DEFAULT_RETRIEVAL_PROGRAM_DIR / "Retrieval.txt"
DEFAULT_UPDATE_SOURCE_PATH = DEFAULT_UPDATE_PROGRAM_DIR / "Update.txt"


# ------------------------------------------------------------- helpers
def existing_files(paths: list[Path]) -> list[Path]:
    """Return only paths that exist and are files."""
    return [
        path
        for path in paths
        if path.exists() and path.is_file()
    ]


def files_in_folder(
    folder: Path,
    extensions: tuple[str, ...],
) -> list[Path]:
    """Return supported files from a folder in stable name order."""
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


# -------------------------------------------------------- mapping sheet
def mapping_sheet_paths() -> list[Path]:
    return files_in_folder(
        DEFAULT_MAPPING_SHEET_DIR,
        SUPPORTED_MAPPING_EXTENSIONS,
    )


def retrieval_mapping_sheet_paths() -> list[Path]:
    mode_paths = files_in_folder(
        DEFAULT_RETRIEVAL_MAPPING_SHEET_DIR,
        SUPPORTED_MAPPING_EXTENSIONS,
    )

    if mode_paths:
        return mode_paths

    return mapping_sheet_paths()


def update_mapping_sheet_paths() -> list[Path]:
    mode_paths = files_in_folder(
        DEFAULT_UPDATE_MAPPING_SHEET_DIR,
        SUPPORTED_MAPPING_EXTENSIONS,
    )

    if mode_paths:
        return mode_paths

    return mapping_sheet_paths()


# ---------------------------------------------------- dclgen / copybook
def dclgen_paths() -> list[Path]:
    return files_in_folder(
        DEFAULT_DCLGEN_DIR,
        SUPPORTED_TEXT_EXTENSIONS,
    )


def copybook_paths() -> list[Path]:
    return files_in_folder(
        DEFAULT_COPYBOOK_DIR,
        SUPPORTED_TEXT_EXTENSIONS,
    )


# ---------------------------------------------------------------- LRF
def lrf_paths() -> list[Path]:
    """LRF subschema files: the LRF folder first, then Subschema."""
    paths = files_in_folder(DEFAULT_LRF_DIR, SUPPORTED_LRF_EXTENSIONS)
    if paths:
        return paths

    return files_in_folder(DEFAULT_SUBSCHEMA_DIR, SUPPORTED_LRF_EXTENSIONS)


def ensure_lrf_dir() -> None:
    """Create the optional LRF folder when it does not exist."""
    DEFAULT_LRF_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------ programs
def retrieval_program_paths() -> list[Path]:
    return files_in_folder(
        DEFAULT_RETRIEVAL_PROGRAM_DIR,
        SUPPORTED_TEXT_EXTENSIONS,
    )


def update_program_paths() -> list[Path]:
    return files_in_folder(
        DEFAULT_UPDATE_PROGRAM_DIR,
        SUPPORTED_TEXT_EXTENSIONS,
    )


# -------------------------------------------------------------- output
def ensure_output_dirs() -> None:
    """Create only the folders the ACTIVE layout uses.

    Creating Output\\Retrieval in flat mode would leave an empty folder
    beside the real output and invite the next reader to look in the
    wrong place.
    """
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if LAYOUT_IS_FLAT:
        return

    DEFAULT_RETRIEVAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_UPDATE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ----------------------------------------------- import-time snapshots
# Kept because retrieval_input_selector.py and update_input_selector.py
# import them directly. They are SNAPSHOTS taken at import; call
# dclgen_paths() / copybook_paths() / lrf_paths() for a live read.
DEFAULT_DCLGEN_CANDIDATE_PATHS = dclgen_paths()
DEFAULT_COPYBOOK_CANDIDATE_PATHS = copybook_paths()
DEFAULT_LRF_CANDIDATE_PATHS = lrf_paths()


__all__ = [
    "PROJECT_ROOT",
    "SRC_DIR",
    "LOGS_DIR",
    "INPUT_DIR_ENV_KEY",
    "LAYOUT_ENV_KEY",
    "INPUT_LAYOUT",
    "LAYOUT_IS_FLAT",
    "DEFAULT_INPUT_DIR",
    "DEFAULT_MAPPING_SHEET_DIR",
    "DEFAULT_RETRIEVAL_MAPPING_SHEET_DIR",
    "DEFAULT_UPDATE_MAPPING_SHEET_DIR",
    "DEFAULT_DCLGEN_DIR",
    "DEFAULT_COPYBOOK_DIR",
    "DEFAULT_LRF_DIR",
    "DEFAULT_SUBSCHEMA_DIR",
    "DEFAULT_PROGRAM_DIR",
    "DEFAULT_RETRIEVAL_PROGRAM_DIR",
    "DEFAULT_UPDATE_PROGRAM_DIR",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_RETRIEVAL_OUTPUT_DIR",
    "DEFAULT_UPDATE_OUTPUT_DIR",
    "DEFAULT_SHEET_MAPPING_PATH",
    "DEFAULT_RETRIEVAL_SOURCE_PATH",
    "DEFAULT_UPDATE_SOURCE_PATH",
    "SUPPORTED_MAPPING_EXTENSIONS",
    "SUPPORTED_TEXT_EXTENSIONS",
    "SUPPORTED_LRF_EXTENSIONS",
    "DEFAULT_DCLGEN_CANDIDATE_PATHS",
    "DEFAULT_COPYBOOK_CANDIDATE_PATHS",
    "DEFAULT_LRF_CANDIDATE_PATHS",
    "existing_files",
    "files_in_folder",
    "mapping_sheet_paths",
    "retrieval_mapping_sheet_paths",
    "update_mapping_sheet_paths",
    "dclgen_paths",
    "copybook_paths",
    "lrf_paths",
    "ensure_lrf_dir",
    "retrieval_program_paths",
    "update_program_paths",
    "ensure_output_dirs",
]