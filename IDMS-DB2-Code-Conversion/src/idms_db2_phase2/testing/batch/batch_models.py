from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BatchMode:
    """Describes one conversion mode (Retrieval or Update)."""

    name: str
    program_dir: Path
    output_dir: Path
    apply_update_postprocess: bool
    default_target_program_id: str = ""


@dataclass
class SharedInputs:
    """Inputs loaded once and shared across every program in a batch."""

    sheet_rows: list
    dclgen_columns: list
    copybook_fields: list
    diagnostics: list[str]