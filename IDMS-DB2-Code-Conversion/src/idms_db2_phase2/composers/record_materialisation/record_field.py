# LOCATION: src/idms_db2_phase2/composers/record_materialisation/record_field.py
# ACTION: CREATE NEW FILE
"""One COBOL data description entry of a materialised record.

Shape and policy only. This class never reads a Sheet Mapping row and
never talks to a resolver - it answers questions ABOUT a field that has
already been read.

ROW SHAPES (Sheet Mapping is a hierarchy, not a flat record)

    1  elementary, mapped        PIC + column      declare + move
    2  group, mapped (dates)     GROUP + column    declare + move
    3  group, structural         GROUP, no column  declare only
    4  subordinate of a group    PIC, no column    declare only
    5  FILLER                    PIC, FILLER cell  declare only
    6  REDEFINES                 PIC, no column    declare only
    7  DB2-only audit/key row    no COBOL zone     neither

GOVERNING PRINCIPLE

    No DB2 column        -> COBOL filler or the breakdown of a mapped
                            parent. Declare it, skip it, never block.
    Column DCLGEN does
    not know             -> a genuine metadata gap. Refuse.
"""

from __future__ import annotations

from dataclasses import dataclass

from rules.record_materialisation_rules import (
    DATE_DB2_TYPE_PREFIX,
    FILLER_FIELD_NAMES,
    NON_COLUMN_SENTINELS,
    NON_DATE_DB2_TYPE_PREFIXES,
)

DEFAULT_LEVEL = "05"
COMP_3_SYMBOL = "COMP-3"


@dataclass
class RecordFieldPlan:
    """One COBOL data description entry of the materialised record."""

    level: str = DEFAULT_LEVEL
    name: str = ""
    picture: str = ""
    usage: str = ""
    redefines: str = ""
    db2_column: str = ""
    db2_type: str = ""
    host_reference: str = ""
    declared_bytes: int = 0

    # ------------------------------------------------------------ shape
    @property
    def is_group(self) -> bool:
        return not self.picture

    @property
    def is_filler(self) -> bool:
        """Shape 5. Occupies bytes, carries no data."""
        return str(self.name or "").strip().upper() in FILLER_FIELD_NAMES

    @property
    def is_redefinition(self) -> bool:
        return bool(self.redefines)

    # ----------------------------------------------------------- column
    @property
    def has_db2_column(self) -> bool:
        """CORRECTION C.

        The literal word FILLER, a dash, N/A and an empty cell are all
        sentinels meaning 'no column'. FILLER was previously looked up
        in DCLGEN, missed, and blocked the entire record.
        """
        candidate = str(self.db2_column or "").strip().upper()
        return candidate not in NON_COLUMN_SENTINELS

    @property
    def is_date(self) -> bool:
        compact = str(self.db2_type or "").upper().replace(" ", "")
        if compact.startswith(NON_DATE_DB2_TYPE_PREFIXES):
            return False
        return compact.startswith(DATE_DB2_TYPE_PREFIX)

    # ----------------------------------------------------------- policy
    @property
    def requires_host(self) -> bool:
        """CORRECTION B.

        Only a REAL DB2 column obliges DCLGEN to supply a host variable.
        A subordinate of a mapped group, a FILLER and a REDEFINES carry
        no column, are never looked up, and can never be reported
        missing.
        """
        if self.is_filler or self.is_redefinition:
            return False
        return self.has_db2_column

    @property
    def is_missing_host(self) -> bool:
        return self.requires_host and not self.host_reference

    @property
    def is_declarable(self) -> bool:
        """Every shape except 7 occupies storage and must be declared."""
        return bool(self.name)

    @property
    def is_movable(self) -> bool:
        """CORRECTION D.

        WAS:  not is_group and host_reference and not redefines
        -> every mapped date GROUP was excluded and the most important
           moves were silently dropped.

        A GROUP carrying a DB2 column IS movable; that is exactly how
        the manual reference populates every date:

            MOVE HULP-DA-VA-FORM-AS TO DA-VA-FORM-AS OF VMBFAS
        """
        if self.is_redefinition:
            return False
        if self.is_filler:
            return False
        if not self.has_db2_column:
            return False
        return bool(self.host_reference)

    @property
    def occupies_storage(self) -> bool:
        """Bytes are counted once, on elementary items only.

        A group's size is the sum of its children, and a REDEFINES
        re-uses storage already counted, so neither may be added again.
        """
        return (
            not self.is_group
            and not self.is_redefinition
            and self.declared_bytes > 0
        )


__all__ = ["COMP_3_SYMBOL", "DEFAULT_LEVEL", "RecordFieldPlan"]