# LOCATION: src/idms_db2_phase2/testing/execution/environment.py
# ACTION: CREATE NEW FILE

"""Paths and child-process environment for batch execution.

Owns the two facts every other execution module needs: where the project
root is, and what environment a runner must be launched with.
"""

from __future__ import annotations

import os
from pathlib import Path

# .../src/idms_db2_phase2/testing/execution/environment.py -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = PROJECT_ROOT / "src"

PYTHONPATH_KEY = "PYTHONPATH"
UNBUFFERED_KEY = "PYTHONUNBUFFERED"

# Both entries are required: the converter lives under src/, while
# rules/, patterns/ and catalogs/ sit at the project root.
PYTHONPATH_ENTRIES = ("src", ".")


def runner_path(relative: str) -> Path:
    """Absolute path to a runner declared in rules/batch_console_rules."""
    return PROJECT_ROOT / relative


def subprocess_environment() -> dict[str, str]:
    """Environment for a runner subprocess.

    PYTHONPATH is set explicitly rather than inherited, so the batch
    behaves identically whether or not the operator set it first.
    Output is unbuffered so a long step still streams its log.
    """
    env = dict(os.environ)

    entries = [
        str(PROJECT_ROOT / entry) if entry != "." else str(PROJECT_ROOT)
        for entry in PYTHONPATH_ENTRIES
    ]

    existing = env.get(PYTHONPATH_KEY, "")
    if existing:
        entries.append(existing)

    env[PYTHONPATH_KEY] = os.pathsep.join(entries)
    env[UNBUFFERED_KEY] = "1"
    return env