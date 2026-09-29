# LOCATION: zowe/zowe_programs.py
# ACTION: CREATE NEW FILE
"""The program array that drives the batch."""

from __future__ import annotations

from pathlib import Path

from zowe.zowe_env import setting
from zowe.zowe_rules import (
    DEFAULT_PROGRAM_LIST_FILE,
    LIBRARY_SEPARATOR,
    NAME_PROGRAM_LIST_FILE,
    NAME_PROGRAMS,
    PROGRAM_LIST_COMMENT,
    ZOWE_ERROR_MESSAGES,
)

PACKAGE_DIR = Path(__file__).resolve().parent


def program_list_file() -> Path:
    name = setting("", NAME_PROGRAM_LIST_FILE, DEFAULT_PROGRAM_LIST_FILE)
    candidate = Path(name)
    return candidate if candidate.is_absolute() else PACKAGE_DIR / name


def selected_programs() -> list[str]:
    """Inline ZOWE_PROGRAMS wins; otherwise the list file is read."""
    inline = setting("", NAME_PROGRAMS)
    if inline:
        return _clean(inline.split(LIBRARY_SEPARATOR))

    path = program_list_file()
    if path.is_file():
        return _clean(path.read_text(encoding="utf-8").splitlines())

    raise ValueError(ZOWE_ERROR_MESSAGES["no_programs"].format(file=path))


def _clean(values) -> list[str]:
    out: list[str] = []
    for raw in values:
        line = str(raw or "").strip()
        if not line or line.startswith(PROGRAM_LIST_COMMENT):
            continue
        name = line.upper()
        if name not in out:
            out.append(name)
    if not out:
        raise ValueError(
            ZOWE_ERROR_MESSAGES["no_programs"].format(file=program_list_file())
        )
    return out