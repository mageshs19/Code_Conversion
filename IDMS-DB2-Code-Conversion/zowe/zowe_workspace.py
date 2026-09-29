# LOCATION: zowe/zowe_workspace.py
# ACTION: REPLACE ENTIRE FILE
"""Workspace layout. Every run artifact lives under zowe/workspace.

One Program folder. No Retrieval / Update split.
Path knowledge only. No HTTP, no COBOL, no subprocess.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from zowe.zowe_env import raw_setting
from zowe.zowe_rules import (
    WORKSPACE_DIR_NAME,
    WORKSPACE_ROOT_KEY,
    WORKSPACE_SUBFOLDERS,
)

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent


def workspace_root() -> Path:
    """Override with ZOWE_WORKSPACE_ROOT, else zowe/workspace."""
    configured = raw_setting(WORKSPACE_ROOT_KEY, "")
    if configured:
        return Path(configured)
    return PACKAGE_DIR / WORKSPACE_DIR_NAME


# ---- Folders ----
def mapping_dir() -> Path:
    return workspace_root() / "Mapping Sheet"


def program_dir() -> Path:
    return workspace_root() / "Program"


def copybook_dir() -> Path:
    return workspace_root() / "Copybook"


def dclgen_dir() -> Path:
    return workspace_root() / "DCLGen"


def subschema_dir() -> Path:
    return workspace_root() / "Subschema"


def output_dir() -> Path:
    return workspace_root() / "Output"


def review_dir() -> Path:
    return workspace_root() / "Review"


def logs_dir() -> Path:
    return workspace_root() / "Logs"


# ---- Maintenance ----
def ensure_workspace() -> list[Path]:
    """Create every folder. Safe to call repeatedly."""
    created: list[Path] = []
    root = workspace_root()

    for sub in WORKSPACE_SUBFOLDERS:
        folder = root / sub
        if not folder.exists():
            created.append(folder)
        folder.mkdir(parents=True, exist_ok=True)

    return created


def clean_generated() -> list[Path]:
    """Remove Output and Review. Never touches inputs."""
    removed: list[Path] = []
    for folder in (output_dir(), review_dir()):
        if folder.exists():
            shutil.rmtree(folder)
            removed.append(folder)
        folder.mkdir(parents=True, exist_ok=True)
    return removed


def count_files(folder: Path, pattern: str = "*") -> int:
    if not folder.exists():
        return 0
    return sum(1 for path in folder.glob(pattern) if path.is_file())