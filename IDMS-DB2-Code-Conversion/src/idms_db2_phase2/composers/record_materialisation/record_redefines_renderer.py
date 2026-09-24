# LOCATION: src/idms_db2_phase2/composers/record_materialisation/record_redefines_renderer.py
# ACTION: CREATE NEW FILE
"""Renders a REDEFINES entry, on one line or two.

CORRECTION 1 - REDEFINES ran into its picture

        10  CT-RK-TGOOD REDEFINES CT-RK-TGDSVPIC 9(4).
                                             ^^^ compile error

    The template carried no separator. A gap is now guaranteed and is
    computed from the remaining body width.

CORRECTION 5 - a REDEFINES entry filled the body exactly

        10  CT-RK-TGOOD REDEFINES CT-RK-TGDSV     PIC 9(4).00900000

    65 characters, no gap before the sequence area, no margin for a
    longer data-name. The manual splits the entry:

        10 CT-RK-TGOOD   REDEFINES CT-RK-TGDSV
                         PIC 9(4).

    render() therefore returns a LIST of lines.
"""

from __future__ import annotations

from idms_db2_phase2.composers.record_materialisation.record_layout_geometry import (
    RecordLayoutGeometry,
)
from rules.record_materialisation_rules import (
    LAYOUT_MIN_NAME_GAP,
    REDEFINES_CONTINUATION_GAP,
    REDEFINES_HEAD_TEMPLATE,
    REDEFINES_INLINE_LIMIT,
    REDEFINES_TEMPLATE,
    WRAP_REDEFINES_ENTRY,
)

REDEFINES_KEYWORD = "REDEFINES"


class RecordRedefinesRenderer:
    """A REDEFINES entry. One line when it fits, two when it does not."""

    def __init__(self, geometry: RecordLayoutGeometry | None = None) -> None:
        self.geometry = geometry or RecordLayoutGeometry()

    # ----------------------------------------------------------- public
    def render(
        self,
        *,
        level: str,
        name: str,
        base: str,
        picture: str,
        indent: str,
    ) -> list[str]:
        clean_picture = str(picture or "").strip()

        if not clean_picture:
            body = f"{level}  {name} {REDEFINES_KEYWORD} {base}"
            return [
                self.geometry.cap(self.geometry.terminate(indent + body))
            ]

        single = self.inline(
            level=level,
            name=name,
            base=base,
            picture=clean_picture,
            indent=indent,
        )

        if not WRAP_REDEFINES_ENTRY:
            return [single]
        if len(single) <= REDEFINES_INLINE_LIMIT:
            return [single]

        return self.wrapped(
            level=level,
            name=name,
            base=base,
            picture=clean_picture,
            indent=indent,
        )

    # ----------------------------------------------------------- inline
    def inline(
        self,
        *,
        level: str,
        name: str,
        base: str,
        picture: str,
        indent: str,
    ) -> str:
        """CORRECTION 1. The gap before the picture is guaranteed."""
        head = f"{indent}{level}  {name} {REDEFINES_KEYWORD} {base}"
        gap = self.geometry.gap_before(head, picture)

        body = REDEFINES_TEMPLATE.format(
            level=level,
            name=name,
            base=base,
            gap=" " * gap,
            picture=picture,
        )
        return self.geometry.cap(self.geometry.terminate(indent + body))

    # ---------------------------------------------------------- wrapped
    def wrapped(
        self,
        *,
        level: str,
        name: str,
        base: str,
        picture: str,
        indent: str,
    ) -> list[str]:
        """CORRECTION 5. Manual reference shape, two lines."""
        gap = " " * max(LAYOUT_MIN_NAME_GAP, REDEFINES_CONTINUATION_GAP)
        head = REDEFINES_HEAD_TEMPLATE.format(
            level=level,
            name=name,
            gap=gap,
            base=base,
        )

        # The continuation aligns under the data-name.
        continuation = indent + (" " * (len(level) + 2))

        return [
            self.geometry.cap(indent + head),
            self.geometry.cap(
                self.geometry.terminate(continuation + picture)
            ),
        ]


__all__ = ["RecordRedefinesRenderer"]