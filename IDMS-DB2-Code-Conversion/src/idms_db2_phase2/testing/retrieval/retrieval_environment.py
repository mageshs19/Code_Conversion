from __future__ import annotations

import sys
from pathlib import Path


def bootstrap_sys_path(current_file: Path) -> tuple[Path, Path]:
    """Ensure PROJECT_ROOT and SRC_DIR are importable.

    Returns (src_dir, project_root).
    """
    resolved = current_file.resolve()
    src_dir = resolved.parents[2]
    project_root = resolved.parents[3]

    for path in (project_root, src_dir):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))

    return src_dir, project_root