# LOCATION: src/idms_db2_phase2/testing/execution/input_inspector.py
# ACTION: CREATE NEW FILE

"""Counts input files and locates artefact folders.

File counts only. Row, column and field TOTALS are reported by the
runners themselves and scraped from their output, so this module never
has to open a workbook or a DCLGEN.

Every lookup degrades to zero or '-' rather than raising: a missing
folder is worth reporting, not worth aborting a batch for.
"""

from __future__ import annotations

from pathlib import Path

from rules.batch_console_rules import VALUE_UNKNOWN

COUNT_KEYS = ("mapping", "dclgen", "copybook", "retrieval", "update")


class InputInspector:
    """Reports what is present in the configured input folders."""

    def counts(self) -> dict[str, int]:
        empty = dict.fromkeys(COUNT_KEYS, 0)

        try:
            from config.path_settings import (
                DEFAULT_COPYBOOK_DIR,
                DEFAULT_DCLGEN_DIR,
                DEFAULT_MAPPING_SHEET_DIR,
                DEFAULT_RETRIEVAL_PROGRAM_DIR,
                DEFAULT_UPDATE_PROGRAM_DIR,
            )
        except Exception:  # noqa: BLE001
            return empty

        return {
            "mapping": self._count(DEFAULT_MAPPING_SHEET_DIR),
            "dclgen": self._count(DEFAULT_DCLGEN_DIR),
            "copybook": self._count(DEFAULT_COPYBOOK_DIR),
            "retrieval": self._count(DEFAULT_RETRIEVAL_PROGRAM_DIR),
            "update": self._count(DEFAULT_UPDATE_PROGRAM_DIR),
        }

    def folders(self) -> tuple[str, str]:
        """(output folder, logs folder)."""
        try:
            from config.path_settings import DEFAULT_OUTPUT_DIR, LOGS_DIR

            return str(DEFAULT_OUTPUT_DIR), str(LOGS_DIR)
        except Exception:  # noqa: BLE001
            return VALUE_UNKNOWN, VALUE_UNKNOWN

    @staticmethod
    def _count(folder) -> int:
        try:
            return sum(1 for path in Path(folder).iterdir() if path.is_file())
        except Exception:  # noqa: BLE001
            return 0