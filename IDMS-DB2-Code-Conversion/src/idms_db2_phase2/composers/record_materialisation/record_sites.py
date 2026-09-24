# LOCATION: src/idms_db2_phase2/composers/record_materialisation/record_sites.py
# ACTION: CREATE NEW FILE
"""Where a whole-record MOVE and its target field live.

Two frozen value objects. They carry no behaviour beyond the two
convenience properties the caller needs, so a scan result can be passed
around without anyone being able to mutate it halfway through a rewrite.
"""

from __future__ import annotations

from dataclasses import dataclass

NOT_FOUND = -1


@dataclass(frozen=True)
class MoveSite:
    """One whole-record MOVE found in the PROCEDURE DIVISION.

        MOVE VMBFAS TO F-FORM
             ^record   ^target
    """

    index: int = NOT_FOUND
    record: str = ""
    target: str = ""

    @property
    def is_found(self) -> bool:
        return self.index > NOT_FOUND

    @property
    def key(self) -> tuple[str, str]:
        """Identity used to remember which moves have been visited.

        The composer iterates until every move has been seen once, so a
        refused record cannot be retried forever.
        """
        return (self.record, self.target)


@dataclass(frozen=True)
class TargetSite:
    """The DATA DIVISION entry a whole-record MOVE writes into.

        05  F-FORM                PIC X(478).
        ^level ^index             ^declared_bytes
    """

    index: int = NOT_FOUND
    declared_bytes: int = 0
    level: int = 0

    @property
    def is_found(self) -> bool:
        return self.index >= 0

    @property
    def has_length(self) -> bool:
        """False means the PICTURE could not be sized.

        The caller must treat that as a diagnostic, never as zero
        remaining bytes - a silent zero is what shortened the record by
        46 bytes with no warning.
        """
        return self.declared_bytes > 0


__all__ = ["NOT_FOUND", "MoveSite", "TargetSite"]