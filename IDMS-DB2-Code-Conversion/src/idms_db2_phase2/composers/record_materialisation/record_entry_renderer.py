# LOCATION: src/idms_db2_phase2/composers/record_materialisation/record_entry_renderer.py
# ACTION: CREATE NEW FILE
"""Renders a group entry and an elementary entry.

Templates plus geometry. Decides nothing about the record as a whole -
it is handed a level, a name, a picture and an indent, and returns one
finished body line.

    06  VMBFAS.
      07  CT-RK-TGDSV             PIC X(4).
      07  FILLER                  PIC X(2).
"""

from __future__ import annotations

from idms_db2_phase2.composers.record_materialisation.record_layout_geometry import (
    RecordLayoutGeometry,
)
from rules.record_materialisation_rules import (
    ELEMENTARY_ITEM_TEMPLATE,
    GROUP_ITEM_TEMPLATE,
)


class RecordEntryRenderer:
    """One data description entry, group or elementary."""

    def __init__(self, geometry: RecordLayoutGeometry | None = None) -> None:
        self.geometry = geometry or RecordLayoutGeometry()

    # ------------------------------------------------------------ group
    def group(self, *, level: str, name: str, indent: str) -> str:
        """`06  VMBFAS.`"""
        body = GROUP_ITEM_TEMPLATE.format(
            level=level,
            name=self.clean_name(name),
        )
        return self.geometry.cap(
            self.geometry.terminate(indent + body)
        )

    # ------------------------------------------------------- elementary
    def elementary(
        self,
        *,
        level: str,
        name: str,
        picture: str,
        indent: str,
    ) -> str:
        """`07  CT-RK-TGDSV             PIC X(4).`

        A blank picture means the sheet declared a group, so the entry
        falls back to the group shape rather than emitting a bare name.
        """
        clean_picture = str(picture or "").strip()
        clean_name = self.clean_name(name)

        if not clean_picture:
            return self.group(level=level, name=clean_name, indent=indent)

        width = self.geometry.name_width(
            indent=indent,
            level=level,
            name=clean_name,
            picture=clean_picture,
        )
        body = ELEMENTARY_ITEM_TEMPLATE.format(
            level=level,
            name=clean_name,
            width=width,
            picture=clean_picture,
        )
        return self.geometry.cap(
            self.geometry.terminate(indent + body)
        )

    # ---------------------------------------------------------- helpers
    @staticmethod
    def picture_of(item) -> str:
        """'PIC S9(13)V99' + 'COMP-3' -> 'PIC S9(13)V99 COMP-3'."""
        picture = str(getattr(item, "picture", "") or "")
        usage = str(getattr(item, "usage", "") or "")
        if not usage:
            return picture.strip()
        return f"{picture} {usage}".strip()

    @staticmethod
    def clean_name(name: str) -> str:
        return str(name or "").strip().upper()


__all__ = ["RecordEntryRenderer"]