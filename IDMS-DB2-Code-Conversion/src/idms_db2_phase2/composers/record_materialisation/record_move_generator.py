# LOCATION: src/idms_db2_phase2/composers/record_materialisation/record_move_generator.py
# ACTION: REPLACE ENTIRE FILE
"""Renders the field-by-field population of a materialised record.

A non-date column becomes a single MOVE. A DB2 DATE column becomes the
manual reference conversion block, using the shared date staging fields
that Db2DateComparisonComposer already declares.

CORRECTION - the continuation line lost its indent

        MOVE CT-RKTGDSV-479BFAS OF DCLDZBFASTV TO
        CT-RK-TGDSV OF VMBFAS          <- same column as the MOVE

    The indent used to live in MOVE_TARGET_TEMPLATE's leading spaces,
    which an unapplied rules override or a later indent pass can flatten.
    It now lives in CODE, applied here, so it cannot be lost.

    A MOVE short enough to fit on one line is emitted on one line, which
    removes the continuation problem entirely for most fields.
"""

from __future__ import annotations

from idms_db2_phase2.composers.record_materialisation.record_field_plan import (
    RecordMaterialisationPlan,
)
from rules.record_materialisation_rules import (
    DATE_CONVERSION_LINE_TEMPLATES,
    DATE_HIGH_NUMERIC_LITERAL,
    DATE_HIGH_VALUE_LITERAL,
    DATE_LOW_VALUE_LITERAL,
    EMIT_DATE_CONVERSION,
    MOVE_CONTINUATION_INDENT,
    MOVE_INLINE_LIMIT,
    MOVE_MARKER_TEMPLATE,
    MOVE_TARGET_TEMPLATE,
    MOVE_TEMPLATE,
)


class RecordMoveGenerator:
    """Builds the MOVE block that populates the materialised record."""

    def generate(self, plan: RecordMaterialisationPlan) -> list[str]:
        """Body lines only. The caller applies indent and the frame."""
        fields = plan.movable_fields
        if not fields:
            return []

        lines: list[str] = [
            MOVE_MARKER_TEMPLATE.format(
                record=plan.record_name,
                group=plan.group_name,
                count=len(fields),
            )
        ]

        for item in fields:
            if EMIT_DATE_CONVERSION and item.is_date:
                lines.extend(self._date_block(plan.record_name, item))
            else:
                lines.extend(self._simple_move(plan.record_name, item))

        return lines

    # ------------------------------------------------------------ moves
    @staticmethod
    def _simple_move(record: str, item) -> list[str]:
        """One line when it fits; head + indented continuation otherwise."""
        source = MOVE_TEMPLATE.format(host=item.host_reference)
        target = MOVE_TARGET_TEMPLATE.format(
            field=item.name,
            record=record,
        ).strip()

        single = f"{source} {target}"
        if len(single) <= MOVE_INLINE_LIMIT:
            return [single]

        return [source, MOVE_CONTINUATION_INDENT + target]

    @staticmethod
    def _date_block(record: str, item) -> list[str]:
        return [
            template.format(
                host=item.host_reference,
                field=item.name,
                record=record,
                low_value=DATE_LOW_VALUE_LITERAL,
                high_value=DATE_HIGH_VALUE_LITERAL,
                high_numeric=DATE_HIGH_NUMERIC_LITERAL,
            )
            for template in DATE_CONVERSION_LINE_TEMPLATES
        ]


__all__ = ["RecordMoveGenerator"]