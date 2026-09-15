# LOCATION: src/idms_db2_phase2/generators/db2_infrastructure/cursor_flag_builder.py
# ACTION: CREATE NEW FILE

"""Builds the end-of-cursor flag group for each cursor.

    01  WS-DZBEFFC1-FLAG               PIC X.
        88  DZBEFFC1-NOT-EOC           VALUE 'N'.
        88  DZBEFFC1-EOC               VALUE 'Y'.

The 01 level is Area A by definition. The 88 condition names are
subordinate entries and belong in Area B, which CHK-06.05 enforces.
"""

from __future__ import annotations

from idms_db2_phase2.generators.db2_infrastructure.cursor_spec import CursorSpec
from rules.db2_infrastructure_rules import (
    CONDITION_TEMPLATE,
    EOC_TEMPLATE,
    FLAG_DECLARATION_TEMPLATE,
    FLAG_NAME_TEMPLATE,
    IND_88_LEVEL,
    NOT_EOC_TEMPLATE,
    VALUE_EOC,
    VALUE_NOT_EOC,
)


class CursorFlagBuilder:
    """Renders one flag group per cursor."""

    def build(self, specs: list[CursorSpec]) -> list[str]:
        lines: list[str] = []

        for spec in specs or []:
            lines.extend(self._group(spec))

        return lines

    # =================================================================
    # One group
    # =================================================================
    def _group(self, spec: CursorSpec) -> list[str]:
        if not spec.cursor_name:
            return []

        cursor = spec.cursor_name

        return [
            FLAG_DECLARATION_TEMPLATE.format(
                name=FLAG_NAME_TEMPLATE.format(cursor=cursor)
            ),
            IND_88_LEVEL
            + CONDITION_TEMPLATE.format(
                name=NOT_EOC_TEMPLATE.format(cursor=cursor),
                value=VALUE_NOT_EOC,
            ),
            IND_88_LEVEL
            + CONDITION_TEMPLATE.format(
                name=EOC_TEMPLATE.format(cursor=cursor),
                value=VALUE_EOC,
            ),
            "",
        ]