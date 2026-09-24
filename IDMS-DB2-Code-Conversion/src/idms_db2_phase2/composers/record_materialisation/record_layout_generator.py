# LOCATION: src/idms_db2_phase2/composers/record_materialisation/record_layout_generator.py
# ACTION: REPLACE ENTIRE FILE
"""Renders the materialised record as COBOL data description entries.

Orchestration only. Every column rule lives in the geometry class and
every template in one of the two renderers:

    record_layout_geometry.py      columns, indents, widths, levels
    record_entry_renderer.py       group + elementary entries
    record_redefines_renderer.py   REDEFINES, inline or wrapped

Public API is unchanged, so record_block_writer.py needs no edit.

CORRECTION 3 - the record is a PREFIX of the target field

    05  F-FORM            PIC X(478).      <- the field being replaced
        06  VMBFAS.                        <- 432 bytes
        07 ...
        06  FILLER        PIC X(46).       <- the remainder, declared here

    Without the remainder FILLER the record silently shortens and every
    following field shifts left.
"""

from __future__ import annotations

from idms_db2_phase2.composers.record_materialisation.record_entry_renderer import (
    RecordEntryRenderer,
)
from idms_db2_phase2.composers.record_materialisation.record_layout_geometry import (
    RecordLayoutGeometry,
)
from idms_db2_phase2.composers.record_materialisation.record_plan import (
    RecordMaterialisationPlan,
)
from idms_db2_phase2.composers.record_materialisation.record_redefines_renderer import (
    RecordRedefinesRenderer,
)
from rules.record_materialisation_rules import (
    EMIT_REMAINDER_FILLER,
    LAYOUT_MARKER_TEMPLATE,
    RECORD_GROUP_LEVEL_STEP,
    REMAINDER_FILLER_NAME,
    REMAINDER_FILLER_PICTURE_TEMPLATE,
)

COMMENT_INDICATOR = "*"
RECORD_GROUP_DEPTH = 1
FIELD_DEPTH_OFFSET = 2


class RecordLayoutGenerator:
    """Builds the COBOL body lines for a materialised record."""

    def __init__(
        self,
        *,
        geometry: RecordLayoutGeometry | None = None,
        entries: RecordEntryRenderer | None = None,
        redefines: RecordRedefinesRenderer | None = None,
    ) -> None:
        self.geometry = geometry or RecordLayoutGeometry()
        self.entries = entries or RecordEntryRenderer(self.geometry)
        self.redefines = redefines or RecordRedefinesRenderer(self.geometry)

    # ================================================================
    # Public
    # ================================================================
    def generate(
        self,
        plan: RecordMaterialisationPlan,
        *,
        base_level: int = 0,
        base_indent: str = "",
    ) -> list[str]:
        """Body lines only. The caller applies the fixed-format frame.

        base_level  - level of the target field being expanded.
        base_indent - body indent of the target field, so the block sits
                      under it instead of jumping to Area A.
        """
        fields = plan.declarable_fields
        if not fields:
            return []

        root = self.geometry.root(base_indent)
        group_level = int(base_level or 0) + RECORD_GROUP_LEVEL_STEP

        lines: list[str] = [
            COMMENT_INDICATOR
            + LAYOUT_MARKER_TEMPLATE.format(record=plan.record_name),
            self.group_line(
                level=group_level,
                name=plan.record_name,
                base_indent=root,
                depth=RECORD_GROUP_DEPTH,
            ),
        ]

        shift = (group_level + 1) - plan.min_level
        stack: list[str] = []

        for item in fields:
            level = self.geometry.shift(item.level, shift)
            depth = self.geometry.depth(stack, level) + FIELD_DEPTH_OFFSET
            # An entry may render as more than one physical line.
            lines.extend(self._entry(item, level, root, depth))

        return lines

    def remainder_line(
        self,
        *,
        level: int,
        byte_count: int,
        base_indent: str = "",
    ) -> list[str]:
        """CORRECTION 3. FILLER for the unused tail of the target field.

        Emitted as a SIBLING of the record group, never inside it.
        """
        if not EMIT_REMAINDER_FILLER:
            return []
        if not byte_count or int(byte_count) <= 0:
            return []

        root = self.geometry.root(base_indent)
        picture = REMAINDER_FILLER_PICTURE_TEMPLATE.format(
            bytes=int(byte_count)
        )
        return [
            self.entries.elementary(
                level=self.geometry.clamp(level),
                name=REMAINDER_FILLER_NAME,
                picture=picture,
                indent=self.geometry.indent_text(root, RECORD_GROUP_DEPTH),
            )
        ]

    def group_line(
        self,
        *,
        level: int,
        name: str,
        base_indent: str = "",
        depth: int = 0,
    ) -> str:
        root = self.geometry.root(base_indent)
        return self.entries.group(
            level=self.geometry.clamp(level),
            name=name,
            indent=self.geometry.indent_text(root, depth),
        )

    # ================================================================
    # One entry
    # ================================================================
    def _entry(self, item, level: str, root: str, depth: int) -> list[str]:
        indent = self.geometry.indent_text(root, depth)
        picture = self.entries.picture_of(item)

        if item.is_redefinition:
            return self.redefines.render(
                level=level,
                name=item.name,
                base=item.redefines,
                picture=picture,
                indent=indent,
            )

        if item.is_group:
            return [
                self.entries.group(
                    level=level,
                    name=item.name,
                    indent=indent,
                )
            ]

        return [
            self.entries.elementary(
                level=level,
                name=item.name,
                picture=picture,
                indent=indent,
            )
        ]


__all__ = ["RecordLayoutGenerator"]