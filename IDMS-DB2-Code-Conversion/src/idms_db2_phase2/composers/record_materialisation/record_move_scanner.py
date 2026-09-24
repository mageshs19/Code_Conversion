# LOCATION: src/idms_db2_phase2/composers/record_materialisation/record_move_scanner.py
# ACTION: REPLACE ENTIRE FILE
"""Locates whole-record MOVE statements and their target fields.

Read-only. Finds sites; rewrites nothing. Sizing lives in
record_picture_sizer.py and the value objects in record_sites.py, so
this class is nothing but two scans.

CORRECTION 1 - first-match-wins

    The original scanner returned the FIRST whole-record MOVE and the
    composer abandoned the whole pass on any refusal. A LINKAGE date
    field matched first, had no Sheet Mapping rows, and the real record
    MOVE was never examined - it then reached the structural safety pass
    and was commented out.

    find_move now takes the set of pairs already visited and returns the
    next unvisited one, so the caller can iterate and a refusal stays
    local to one record.
"""

from __future__ import annotations

import re

from idms_db2_phase2.composers.record_materialisation.record_line_utils import (
    RecordLineUtils,
)
from idms_db2_phase2.composers.record_materialisation.record_picture_sizer import (
    RecordPictureSizer,
)
from idms_db2_phase2.composers.record_materialisation.record_sites import (
    MoveSite,
    TargetSite,
)
from patterns.record_materialisation_patterns import (
    PROCEDURE_DIVISION_PATTERN,
    TARGET_FIELD_PATTERN_TEMPLATE,
    WHOLE_RECORD_MOVE_PATTERN,
)


class RecordMoveScanner:
    """Finds whole-record MOVEs and the fields they write into."""

    def __init__(
        self,
        line_utils: RecordLineUtils | None = None,
        sizer: RecordPictureSizer | None = None,
    ) -> None:
        self.lines = line_utils or RecordLineUtils()
        self.sizer = sizer or RecordPictureSizer()

    # ------------------------------------------------------------- move
    def find_move(
        self,
        lines: list[str],
        handled: set[tuple[str, str]],
    ) -> MoveSite | None:
        """Next whole-record MOVE not yet visited. None when exhausted."""
        in_procedure = False

        for index, line in enumerate(lines):
            if self.lines.is_skippable(line):
                continue

            body = self.lines.logical(line)
            if not body:
                continue

            if PROCEDURE_DIVISION_PATTERN.match(body):
                in_procedure = True
                continue

            if not in_procedure:
                continue

            match = WHOLE_RECORD_MOVE_PATTERN.match(body)
            if not match:
                continue

            site = MoveSite(
                index=index,
                record=match.group("record").upper(),
                target=match.group("target").upper(),
            )
            if site.key in handled:
                continue

            return site

        return None

    # ----------------------------------------------------------- target
    def find_target(self, lines: list[str], target: str) -> TargetSite:
        """The DATA DIVISION entry for `target`, or an empty TargetSite."""
        pattern = self._target_pattern(target)

        for index, line in enumerate(lines):
            if self.lines.is_skippable(line):
                continue

            body = self.lines.logical(line)
            if not body:
                continue

            # The DATA DIVISION ends here; stop rather than match a
            # PROCEDURE DIVISION reference to the same name.
            if PROCEDURE_DIVISION_PATTERN.match(body):
                break

            match = pattern.match(body)
            if not match:
                continue

            return TargetSite(
                index=index,
                declared_bytes=self.sizer.declared_bytes(body, match),
                level=self.lines.level_of(body),
            )

        return TargetSite()

    # ---------------------------------------------------------- helpers
    @staticmethod
    def _target_pattern(target: str):
        return re.compile(
            TARGET_FIELD_PATTERN_TEMPLATE.format(name=re.escape(target)),
            flags=re.IGNORECASE,
        )

    # Preserved for callers that still import it from this module.
    @classmethod
    def picture_bytes(cls, picture: str) -> int:
        return RecordPictureSizer.size_of(picture, picture)


__all__ = ["MoveSite", "RecordMoveScanner", "RecordPictureSizer", "TargetSite"]