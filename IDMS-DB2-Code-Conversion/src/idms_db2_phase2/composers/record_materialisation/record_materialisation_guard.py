# LOCATION: src/idms_db2_phase2/composers/record_materialisation/record_materialisation_guard.py
# ACTION: CREATE NEW FILE
"""Decides whether one record may be materialised.

Every gate REFUSES rather than guesses. A refusal leaves working COBOL
and a diagnostic; a guess corrupts a fixed-length output record.

CORRECTION A - the length rule was equality

    The IDMS record is a PREFIX of the output field, never equal to it:

        05  F-FORM   PIC X(478).
            06  VMBFAS.            <- 432 bytes

    |432 - 478| = 46 > 0 guaranteed refusal on every run. The layout may
    be SHORTER; only LONGER is fatal, because that shifts every byte
    after it.

CORRECTION B + C - unmapped subordinates and FILLER blocked

    A field is missing ONLY when it carries a real DB2 column that DCLGEN
    does not define. No column at all means COBOL filler or the
    breakdown of a mapped parent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rules.record_materialisation_rules import (
    ALLOW_LAYOUT_SHORTER_THAN_TARGET,
    ENFORCE_LENGTH_MATCH,
    LENGTH_TOLERANCE,
)

MISSING_HOST_SAMPLE = 5


@dataclass(frozen=True)
class Refusal:
    """A named diagnostic plus its template values."""

    key: str = ""
    values: dict = field(default_factory=dict)


class RecordMaterialisationGuard:
    """All refusal decisions for one record, in evaluation order."""

    def __init__(self, plan_builder) -> None:
        self.plan_builder = plan_builder

    # ------------------------------------------------------------ plan
    def build_plan(self, record: str):
        """(plan, refusal). plan is None when the record is refused."""
        if not self.plan_builder.looks_like_record(record):
            return None, Refusal(
                "skipped_not_a_record", {"record": record}
            )

        plan = self.plan_builder.build(record)

        if not plan.fields:
            return None, Refusal("skipped_no_mapping", {"record": record})

        if not plan.group_name:
            return None, Refusal("skipped_no_group", {"record": record})

        if plan.missing_hosts:
            return None, Refusal(
                "skipped_incomplete",
                {
                    "record": record,
                    "missing": len(plan.missing_hosts),
                    "names": ", ".join(
                        plan.missing_hosts[:MISSING_HOST_SAMPLE]
                    ),
                },
            )

        return plan, None

    # ---------------------------------------------------------- length
    @staticmethod
    def check_length(plan, target: str, declared_bytes: int):
        """Refusal when the layout is LONGER than the target field."""
        if not ENFORCE_LENGTH_MATCH or not declared_bytes:
            return None

        too_long = plan.overflows(declared_bytes, LENGTH_TOLERANCE)
        too_short = (
            not ALLOW_LAYOUT_SHORTER_THAN_TARGET
            and plan.remainder_bytes(declared_bytes) > LENGTH_TOLERANCE
        )

        if not (too_long or too_short):
            return None

        return Refusal(
            "skipped_too_long",
            {
                "record": plan.record_name,
                "actual": plan.total_bytes,
                "target": target,
                "expected": declared_bytes,
            },
        )

    # ---------------------------------------------------------- advice
    @staticmethod
    def check_movable(plan):
        """Not a refusal. A visible warning that nothing is populated."""
        if plan.movable_fields:
            return None
        return Refusal(
            "declared_only",
            {
                "record": plan.record_name,
                "fields": len(plan.declarable_fields),
            },
        )


__all__ = ["Refusal", "RecordMaterialisationGuard"]