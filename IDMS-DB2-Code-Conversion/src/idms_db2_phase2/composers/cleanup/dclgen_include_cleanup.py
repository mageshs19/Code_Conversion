"""DCLGEN include cleanup.

Ensures an EXEC SQL INCLUDE exists for every referenced DCLGEN group that
the DCLGEN repository knows about but that is not already included.

CORRECTION 1 - third include shape
----------------------------------
This pass emitted its own three-line block with a single leading space,
placing EXEC SQL at column 9. CHK-06.07 requires Area B, column 12.

CORRECTION 2 - single-shape duplicate detection
-----------------------------------------------
_existing_includes recognised one shape only, so an include already
emitted elsewhere was added again. A duplicated DCLGEN include duplicates
every data-name in the group, which the compiler rejects. CHK-08.02
reported this as DZBFARTV x2.

CORRECTION 3 - borrowed capture group
-------------------------------------
_referenced_dclgen_tables read match.group("group") from
patterns.cobol_cleanup_patterns.DCL_GROUP_PATTERN, which does not declare
that name, raising "IndexError: no such group". It now uses
DCLGEN_GROUP_PATTERN from patterns/db2_include_patterns.py, owned
alongside this feature.

CORRECTION 4 - include injected outside WORKING-STORAGE
-------------------------------------------------------
_db2_include_insert_index scanned the WHOLE program for the last include
block, then inserted after it.

That was safe while every include lived in WORKING-STORAGE. It stopped
being safe once the SQLERROR routine adopted the copybook form:

    * SQLERROR ROUTINE.
        EXEC SQL
             INCLUDE SQLERROR
        END-EXEC.

That is an INCLUDE inside an EXEC SQL block, sitting in the PROCEDURE
DIVISION at the end of the program. The scan found it as "the last
include" and injected DZBFARTV after it, past the end of WORKING-STORAGE.
CHK-08.03 reported the include as not sitting inside WORKING-STORAGE.

The scan is now bounded: it stops at LINKAGE SECTION or PROCEDURE
DIVISION, whichever comes first, and falls back to inserting at that
boundary.
"""

from __future__ import annotations

from catalogs.output_sections import DCLGEN_GROUP_PREFIX
from idms_db2_phase2.composers.cleanup.cleanup_message_collector import (
    CleanupMessageCollector,
)
from idms_db2_phase2.composers.cleanup.cobol_cleanup_line_utils import (
    CobolCleanupLineUtils,
)
from idms_db2_phase2.generators.db2_infrastructure.include_renderer import (
    IncludeRenderer,
)
from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.db2_include_patterns import DCLGEN_GROUP_PATTERN

TOKEN_EXEC_SQL = "EXEC SQL"
TOKEN_END_EXEC = "END-EXEC"
TOKEN_INCLUDE = "INCLUDE "

# Boundaries of the area a DCLGEN include may occupy. Matched against the
# uppercased logical line, so no regex dependency is introduced.
TOKEN_LINKAGE_SECTION = "LINKAGE SECTION"
TOKEN_PROCEDURE_DIVISION = "PROCEDURE DIVISION"

DATA_AREA_BOUNDARIES = (
    TOKEN_LINKAGE_SECTION,
    TOKEN_PROCEDURE_DIVISION,
)


class DclgenIncludeCleanup:
    """Adds a missing DCLGEN include, exactly once, inside WORKING-STORAGE."""

    def __init__(
        self,
        dclgen_repository: DclgenRepository,
        messages: CleanupMessageCollector,
        line_utils: CobolCleanupLineUtils | None = None,
    ) -> None:
        self.dclgen_repository = dclgen_repository
        self.messages = messages
        self.line_utils = line_utils or CobolCleanupLineUtils()

        # Shared with InfrastructureBlockBuilder and the update storage
        # injector, so shape, indent and duplicate test live in one place.
        self.includes = IncludeRenderer(self.line_utils)

    # =================================================================
    # Public entry point
    # =================================================================
    def apply(self, text: str) -> str:
        if not text:
            return ""

        lines = str(text).splitlines()
        existing = self.includes.existing(lines)

        missing = [
            table
            for table in self._referenced_dclgen_tables(lines)
            if table not in existing
            and self.dclgen_repository.has_table(table)
        ]

        if not missing:
            return text

        include_lines: list[str] = []
        for table in missing:
            include_lines.extend(self.includes.render(table))
            self.messages.add("added_dclgen_include", table=table)

        insert_index = self._db2_include_insert_index(lines)

        if insert_index < 0:
            return text.rstrip() + "\n" + "\n".join(include_lines) + "\n"

        updated = lines[:insert_index] + include_lines + lines[insert_index:]
        return "\n".join(updated).rstrip() + "\n"

    # =================================================================
    # Scanning
    # =================================================================
    def _referenced_dclgen_tables(self, lines: list[str]) -> list[str]:
        """Table names implied by DCLGEN host group references.

        DCLDZBFARTV -> DZBFARTV. Order preserved, de-duplicated.
        """
        output: list[str] = []
        seen: set[str] = set()

        for line in lines:
            logical = self._logical(line)
            if not logical:
                continue

            for match in DCLGEN_GROUP_PATTERN.finditer(logical):
                group = NameNormalizer.normalize(
                    str(match.group("group") or "")
                ).upper()

                if not group.startswith(DCLGEN_GROUP_PREFIX):
                    continue

                table = group[len(DCLGEN_GROUP_PREFIX):]
                if not table or table in seen:
                    continue

                # DCLGEN itself strips to GEN, which is infrastructure,
                # not a table. So do SQLCA, SQLERRWS and SQLERROR.
                if self.includes.is_infrastructure(table):
                    continue

                seen.add(table)
                output.append(table)

        return output

    def _existing_includes(self, text: str) -> set[str]:
        """Every include already present, whichever shape carries it.

        Retained for callers outside this class.
        """
        return self.includes.existing(str(text or "").splitlines())

    # =================================================================
    # Placement
    # =================================================================
    def _data_area_boundary(self, lines: list[str]) -> int:
        """Index of the first line that ends the DATA DIVISION area.

        A DCLGEN include must sit inside WORKING-STORAGE. Anything from
        LINKAGE SECTION onward is out of bounds, and so is the whole
        PROCEDURE DIVISION.
        """
        for index, line in enumerate(lines):
            logical = self._logical(line).upper()
            if not logical:
                continue

            if logical.startswith(DATA_AREA_BOUNDARIES):
                return index

        return len(lines)

    def _db2_include_insert_index(self, lines: list[str]) -> int:
        """Insert after the last include INSIDE the data area.

        Bounded deliberately. The SQLERROR routine carries an
        EXEC SQL INCLUDE SQLERROR block in the PROCEDURE DIVISION, so an
        unbounded scan reported that as the last include and injected the
        DCLGEN include after it, outside WORKING-STORAGE.

        Handles both the single-line and the three-line block form. The
        original tracked only multi-line blocks, so once includes became
        single-line it could not find the end of the group.
        """
        boundary = self._data_area_boundary(lines)

        last_include_end = -1
        in_exec_sql = False
        include_seen_in_block = False

        for index in range(boundary):
            logical = self._logical(lines[index]).upper()
            if not logical:
                continue

            if logical.startswith(TOKEN_EXEC_SQL):
                in_exec_sql = True
                include_seen_in_block = TOKEN_INCLUDE in logical

                if TOKEN_END_EXEC in logical:
                    if include_seen_in_block:
                        last_include_end = index + 1
                    in_exec_sql = False
                    include_seen_in_block = False
                continue

            if in_exec_sql and TOKEN_INCLUDE in logical:
                include_seen_in_block = True

            if in_exec_sql and logical.startswith(TOKEN_END_EXEC):
                if include_seen_in_block:
                    last_include_end = index + 1
                in_exec_sql = False
                include_seen_in_block = False

        if last_include_end >= 0:
            return last_include_end

        # No include yet: place the block immediately before LINKAGE
        # SECTION or PROCEDURE DIVISION, whichever ends the data area.
        if boundary < len(lines):
            return boundary

        return -1

    # =================================================================
    # Helpers
    # =================================================================
    def _logical(self, line: str) -> str:
        return self.line_utils.logical(line)