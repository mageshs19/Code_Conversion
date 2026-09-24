# LOCATION: src/idms_db2_phase2/composers/record_materialisation/record_row_reader.py
# ACTION: CREATE NEW FILE
"""Turns one Sheet Mapping row into a RecordFieldPlan.

Sheet Mapping is the authority for the COBOL layout (cobol_zone,
idms_pic_clause) and the DB2 column. Nothing is invented: a cell the
sheet does not supply becomes an empty string, never a guess.

CORRECTION - the byte fallback trusted one repeat pattern

    _bytes fell back to PICTURE_REPEAT_PATTERN, which only sees an
    explicit '(nnn)'. That reads 'X(10)' correctly but returns 3 for
    'XXX' and 13 for 'S9(13)V99' (the trailing V99 is invisible).

    The fallback now counts every stored symbol with its repeat, the
    same way RecordMoveScanner sizes a target PICTURE. The sheet's own
    length column still wins when it is present.
"""

from __future__ import annotations

from idms_db2_phase2.composers.record_materialisation.record_field import (
    COMP_3_SYMBOL,
    DEFAULT_LEVEL,
    RecordFieldPlan,
)
from patterns.record_materialisation_patterns import (
    COBOL_ZONE_PATTERN,
    COBOL_ZONE_REDEFINES_PATTERN,
    PICTURE_PATTERN,
    PICTURE_SYMBOL_PATTERN,
)
from rules.record_materialisation_rules import GROUP_PICTURE_TOKENS

COUNTED_SYMBOLS = ("X", "9", "A", "Z")


class RecordRowReader:
    """Reads Sheet Mapping rows. Resolves nothing, decides nothing."""

    # ----------------------------------------------------------- public
    def read(self, row) -> RecordFieldPlan | None:
        """A field, or None when the row declares no COBOL storage.

        None means SHAPE 7: a DB2-only audit or surrogate-key row
        (TS_CREATE, TS_UPDATE, ID_USERID, the Foreign Key rows). It
        exists in the table, not in the record.
        """
        zone = str(getattr(row, "cobol_zone", "") or "").strip()
        if not zone:
            return None

        level, name, base = self._split_zone(zone)
        if not name:
            return None

        picture, usage = self.picture(
            str(getattr(row, "idms_pic_clause", "") or "")
        )

        return RecordFieldPlan(
            level=str(level).strip().zfill(2),
            name=name,
            picture=picture,
            usage=usage,
            redefines=base,
            db2_column=self.column(row),
            db2_type=str(getattr(row, "new_db2_data_type", "") or ""),
            declared_bytes=self.declared_bytes(row, picture, usage),
        )

    # ------------------------------------------------------------- zone
    @staticmethod
    def _split_zone(zone: str) -> tuple[str, str, str]:
        """'05 CT-RK-TGOOD REDEFINES CT-RK-TGDSV' -> (level, name, base)."""
        redefines = COBOL_ZONE_REDEFINES_PATTERN.match(zone)
        if redefines:
            return (
                redefines.group("level") or DEFAULT_LEVEL,
                redefines.group("name").upper(),
                redefines.group("base").upper(),
            )

        plain = COBOL_ZONE_PATTERN.match(zone)
        if not plain:
            return DEFAULT_LEVEL, "", ""

        return (
            plain.group("level") or DEFAULT_LEVEL,
            plain.group("name").upper(),
            "",
        )

    # ---------------------------------------------------------- picture
    @staticmethod
    def picture(clause: str) -> tuple[str, str]:
        """'PIC S9(13)V99 COMP-3' -> ('PIC S9(13)V99', 'COMP-3')."""
        text = str(clause or "").strip().upper()
        if not text or text in GROUP_PICTURE_TOKENS:
            return "", ""

        match = PICTURE_PATTERN.search(text)
        if not match:
            return "", ""

        return (
            f"PIC {match.group('picture')}",
            str(match.group("usage") or "").strip(),
        )

    # ----------------------------------------------------------- column
    @staticmethod
    def column(row) -> str:
        return str(
            getattr(row, "new_db2_field_name", "")
            or getattr(row, "cross_application_db2_field_name", "")
            or ""
        ).strip().upper()

    # ------------------------------------------------------------ bytes
    @classmethod
    def declared_bytes(cls, row, picture: str, usage: str) -> int:
        """The sheet's length column, or the PICTURE when it is blank."""
        declared = str(
            getattr(row, "length_of_field_bytes", "") or ""
        ).strip()
        if declared.isdigit():
            return int(declared)
        return cls.picture_bytes(picture, usage)

    @staticmethod
    def picture_bytes(picture: str, usage: str = "") -> int:
        """Character positions of a PICTURE, honouring repeat counts.

            X(10)       -> 10
            XXX         ->  3
            S9(13)V99   -> 15   (S and V are not stored)
        """
        text = str(picture or "").upper()
        if not text:
            return 0

        digits = 0
        for found in PICTURE_SYMBOL_PATTERN.finditer(text):
            symbol = str(found.group("symbol") or "").upper()
            if symbol not in COUNTED_SYMBOLS:
                continue
            repeat = found.group("repeat")
            digits += int(repeat) if repeat and repeat.isdigit() else 1

        if not digits:
            return 0
        if COMP_3_SYMBOL in str(usage or "").upper():
            return (digits // 2) + 1
        return digits


__all__ = ["RecordRowReader"]