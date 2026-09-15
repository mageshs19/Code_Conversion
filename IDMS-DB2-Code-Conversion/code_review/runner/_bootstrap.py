"""Shared constants and small file helpers for the code review runners.

No sys.path work happens in this module.

Each runner performs its own inline sys.path bootstrap at the very top of
its file, before any code_review import, because running

    python code_review\\runner\\review_file.py

puts only code_review\\runner on sys.path. Doing it here as well would be
a second, competing mechanism that runs too late to help.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

# ---- Locations -------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
REPORT_DIR = PROJECT_ROOT / "code_review" / "report" / "output"

# ---- Formats ---------------------------------------------------------
TIMESTAMP_FORMAT = "%d-%m-%Y_%H%M%S"
COBOL_GLOB = "*.cbl"
TEXT_ENCODING = "utf-8"

# ---- Exit codes ------------------------------------------------------
EXIT_ACCEPTED = 0
EXIT_REJECTED = 1
EXIT_ERROR = 2


def stamp() -> str:
    """Timestamp used in report file names."""
    return datetime.now().strftime(TIMESTAMP_FORMAT)


def read_text(path: Path) -> str:
    """Read a COBOL or text file without ever raising on bad bytes."""
    return Path(path).read_text(encoding=TEXT_ENCODING, errors="replace")