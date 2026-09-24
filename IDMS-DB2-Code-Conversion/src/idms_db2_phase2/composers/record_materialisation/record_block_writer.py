# LOCATION: src/idms_db2_phase2/composers/record_materialisation/record_block_writer.py
# ACTION: CREATE NEW FILE
"""Rewrites the MOVE statement and expands the target field.

CORRECTION 1 - the expanded header lost its indent

    Generated output read

        000820 01  REC-FORM.
        000830 05  F-FORM.        <- column 8, Area A

    Level 01 and 77 start in Area A; levels 02-49 must start in Area B.
    The target's own body indent is now reused for the header, the
    layout block and the remainder FILLER, so the expansion sits exactly
    where the field it replaces sat.

CORRECTION 2 - the MOVE continuation lost its indent

        MOVE CT-RKTGDSV-479BFAS OF DCLDZBFASTV TO
        CT-RK-TGDSV OF VMBFAS          <- same column as MOVE

    The generator's own leading spaces are preserved, so the statement
    reads as one MOVE.

CORRECTION 3 - the record is a PREFIX of the target

    478 - 432 = 46 trailing bytes are declared as FILLER, so the record
    keeps its length and no following byte shifts.
"""

from __future__ import annotations

from idms_db2_phase2.composers.record_materialisation.record_line_utils import (
    RecordLineUtils,
)
from rules.record_materialisation_rules import (
    MOVE_INDENT,
    RECORD_GROUP_LEVEL_STEP,
)


class RecordBlockWriter:
    """Produces the replacement lines. Decides nothing."""

    def __init__(
        self,
        *,
        layout_generator,
        move_generator,
        line_utils: RecordLineUtils | None = None,
    ) -> None:
        self.layout_generator = layout_generator
        self.move_generator = move_generator
        self.lines = line_utils or RecordLineUtils()

    # ------------------------------------------------------------ move
    def replace_move(
        self,
        lines: list[str],
        index: int,
        plan,
    ) -> list[str]:
        """Swap the whole-record MOVE for the field-by-field block."""
        template = lines[index]
        indent = self.lines.body_indent(template) or MOVE_INDENT

        rendered: list[str] = []
        for body in self.move_generator.generate(plan):
            stripped = body.lstrip()
            if stripped.startswith("*"):
                rendered.extend(
                    self.lines.emit(template, stripped.lstrip("*"), "*")
                )
                continue
            # CORRECTION 2: body keeps its own leading spaces, so a
            # continuation line stays indented under its MOVE.
            rendered.extend(self.lines.emit(template, indent + body))

        return lines[:index] + rendered + lines[index + 1:]

    # ---------------------------------------------------------- target
    def expand_target(
        self,
        lines: list[str],
        index: int,
        target: str,
        plan,
        *,
        target_level: int = 0,
        declared_bytes: int = 0,
    ) -> list[str]:
        """Replace `05 F-FORM PIC X(478).` with the real layout."""
        template = lines[index]
        body = self.lines.logical(template)
        level = body.split()[0] if body.split() else ""

        # CORRECTION 1: reuse the target's own indent.
        indent = self.lines.body_indent(template) or MOVE_INDENT
        base_level = target_level or self.lines.level_of(body)

        rendered: list[str] = list(
            self.lines.emit(template, f"{indent}{level}  {target}.")
        )

        for text in self.layout_generator.generate(
            plan,
            base_level=base_level,
            base_indent=indent,
        ):
            rendered.extend(self.lines.emit_generated(template, text))

        # CORRECTION 3: close the record out to the declared length.
        for text in self.layout_generator.remainder_line(
            level=base_level + RECORD_GROUP_LEVEL_STEP,
            byte_count=plan.remainder_bytes(declared_bytes),
            base_indent=indent,
        ):
            rendered.extend(self.lines.emit(template, text))

        return lines[:index] + rendered + lines[index + 1:]


__all__ = ["RecordBlockWriter"]