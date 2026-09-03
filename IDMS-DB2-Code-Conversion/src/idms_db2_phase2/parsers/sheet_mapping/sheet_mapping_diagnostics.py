from __future__ import annotations

from idms_db2_phase2.domain.models import SheetMappingRow
from rules.sheet_mapping_parser_rules import (
    POPULATION_DIAGNOSTIC_SPEC,
    USEFUL_CONTEXT_GROUPS,
    USEFUL_CONTEXT_LABEL,
)


class SheetMappingDiagnostics:
    """Population diagnostics driven by a spec (no per-metric repetition)."""

    def _add_population_diagnostics(self, rows: list[SheetMappingRow]) -> None:
        for label, attrs in POPULATION_DIAGNOSTIC_SPEC:
            count = sum(1 for row in rows if self._any_attr_set(row, attrs))
            self.diagnostics.append(f"{label}: {count}")

        useful = sum(
            1
            for row in rows
            if all(self._any_attr_set(row, group) for group in USEFUL_CONTEXT_GROUPS)
        )
        self.diagnostics.append(f"{USEFUL_CONTEXT_LABEL}: {useful}")

    @staticmethod
    def _any_attr_set(row: SheetMappingRow, attrs: list[str]) -> bool:
        return any(str(getattr(row, attr, "") or "").strip() for attr in attrs)