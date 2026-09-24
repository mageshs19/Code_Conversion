# LOCATION: src/idms_db2_phase2/composers/record_materialisation/record_plan.py
# ACTION: CREATE NEW FILE
"""Everything needed to materialise one record.

A value object. It aggregates RecordFieldPlan values and answers the
size questions the guard asks; it never builds itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from idms_db2_phase2.composers.record_materialisation.record_field import (
    DEFAULT_LEVEL,
    RecordFieldPlan,
)
from rules.record_materialisation_rules import (
    REQUIRE_COMPLETE_FIELD_COVERAGE,
)


@dataclass
class RecordMaterialisationPlan:
    """Fields, diagnostics and sizes for one materialised record."""

    record_name: str = ""
    table_name: str = ""
    group_name: str = ""
    fields: list[RecordFieldPlan] = field(default_factory=list)
    missing_hosts: list[str] = field(default_factory=list)
    skipped_rows: int = 0

    # ------------------------------------------------------------ views
    @property
    def declarable_fields(self) -> list[RecordFieldPlan]:
        return [item for item in self.fields if item.is_declarable]

    @property
    def movable_fields(self) -> list[RecordFieldPlan]:
        return [item for item in self.fields if item.is_movable]

    @property
    def filler_fields(self) -> list[RecordFieldPlan]:
        return [item for item in self.fields if item.is_filler]

    # ------------------------------------------------------------ sizes
    @property
    def total_bytes(self) -> int:
        return sum(
            item.declared_bytes
            for item in self.fields
            if item.occupies_storage
        )

    @property
    def min_level(self) -> int:
        """Shallowest level in the mapping, used to rebase the layout."""
        levels = [
            int(str(item.level).strip())
            for item in self.declarable_fields
            if str(item.level).strip().isdigit()
        ]
        return min(levels) if levels else int(DEFAULT_LEVEL)

    # ----------------------------------------------------------- checks
    @property
    def is_complete(self) -> bool:
        if not REQUIRE_COMPLETE_FIELD_COVERAGE:
            return True
        return not self.missing_hosts

    def remainder_bytes(self, declared_bytes: int) -> int:
        """Unused trailing bytes of the target field. Never negative.

        The IDMS record is a PREFIX of the output field:

            05  F-FORM   PIC X(478).
                06  VMBFAS.            <- 432 bytes
                06  FILLER  PIC X(46). <- this remainder

        Without the remainder the record silently shortens and every
        following field shifts.
        """
        if not declared_bytes or int(declared_bytes) <= 0:
            return 0
        return max(0, int(declared_bytes) - self.total_bytes)

    def overflows(self, declared_bytes: int, tolerance: int = 0) -> bool:
        """True ONLY when the layout is LONGER than the target field.

        Shorter is normal and is closed with FILLER, never refused.
        """
        if not declared_bytes or int(declared_bytes) <= 0:
            return False
        return (self.total_bytes - int(declared_bytes)) > int(tolerance)


__all__ = ["RecordMaterialisationPlan"]