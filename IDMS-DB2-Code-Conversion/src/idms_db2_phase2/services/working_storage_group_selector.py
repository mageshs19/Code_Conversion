# LOCATION: src/idms_db2_phase2/services/working_storage_group_selector.py
# ACTION: CREATE NEW FILE
"""Chooses a SAFE 01 group for generated working-storage fields.

A generated counter must never be added to a record layout. Adding a
field to a fixed-length record shifts every byte after it, silently
corrupting the output file.

An 01 group is a record layout when any of these hold:

  * it is declared under FD / FILE SECTION,
  * it is the operand of WRITE / READ / REWRITE / RELEASE / RETURN,
  * it appears as WRITE ... FROM <name> or READ ... INTO <name>,
  * it is the target of MOVE SPACES / ZEROES TO <name>.

When no safe group exists the selector reports that a dedicated group
must be created. It never guesses.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from patterns.structural_safety_patterns import (
    FD_PATTERN,
    FILE_SECTION_PATTERN,
    LEVEL_01_PATTERN,
    LINKAGE_SECTION_PATTERN,
    MOVE_WHOLE_GROUP_PATTERN,
    PROCEDURE_DIVISION_PATTERN,
    READ_INTO_PATTERN,
    RECORD_VERB_PATTERN,
    SUBORDINATE_LEVEL_PATTERN,
    WORKING_STORAGE_PATTERN,
    WRITE_FROM_PATTERN,
)

COMMENT_PREFIXES = ("*", "/")


@dataclass
class WorkingStorageGroup:
    name: str = ""
    header_index: int = -1
    last_child_index: int = -1
    child_level: str = ""
    is_record_layout: bool = False

    @property
    def is_safe(self) -> bool:
        return bool(self.name) and not self.is_record_layout

    @property
    def insert_index(self) -> int:
        if self.last_child_index >= 0:
            return self.last_child_index + 1
        return self.header_index + 1


@dataclass
class WorkingStorageLayout:
    groups: list[WorkingStorageGroup] = field(default_factory=list)
    working_storage_index: int = -1
    boundary_index: int = -1

    def safe_groups(self) -> list[WorkingStorageGroup]:
        return [group for group in self.groups if group.is_safe]


class WorkingStorageGroupSelector:
    """Maps WORKING-STORAGE and classifies every 01 group."""

    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.fixed_format = fixed_format or FixedFormatLineService()

    # ---------------------------------------------------------- public
    def analyze(self, lines: list[str]) -> WorkingStorageLayout:
        layout = WorkingStorageLayout()
        record_names = self._record_layout_names(lines)

        in_working_storage = False
        in_file_section = False
        current: WorkingStorageGroup | None = None

        for index, line in enumerate(lines):
            body = self._logical(line)
            if not body or self._is_comment(body):
                continue

            if FILE_SECTION_PATTERN.match(body):
                in_file_section = True
                in_working_storage = False
                continue

            if WORKING_STORAGE_PATTERN.match(body):
                in_file_section = False
                in_working_storage = True
                layout.working_storage_index = index
                continue

            if LINKAGE_SECTION_PATTERN.match(body) or (
                PROCEDURE_DIVISION_PATTERN.match(body)
            ):
                layout.boundary_index = index
                break

            if in_file_section or FD_PATTERN.match(body):
                continue

            if not in_working_storage:
                continue

            match = LEVEL_01_PATTERN.match(body)
            if match:
                name = match.group("name").upper()
                current = WorkingStorageGroup(
                    name=name,
                    header_index=index,
                    is_record_layout=name in record_names,
                )
                layout.groups.append(current)
                continue

            child = SUBORDINATE_LEVEL_PATTERN.match(body)
            if child and current is not None:
                current.last_child_index = index
                if not current.child_level:
                    current.child_level = child.group("level")

        if layout.boundary_index < 0:
            layout.boundary_index = len(lines)

        return layout

    def select(self, lines: list[str]) -> WorkingStorageGroup | None:
        """The LAST safe work group, or None when one must be created."""
        safe = self.analyze(lines).safe_groups()
        return safe[-1] if safe else None

    # -------------------------------------------------------- helpers
    def _record_layout_names(self, lines: list[str]) -> set[str]:
        names: set[str] = set()
        in_file_section = False

        for line in lines:
            body = self._logical(line)
            if not body or self._is_comment(body):
                continue

            if FILE_SECTION_PATTERN.match(body):
                in_file_section = True
            elif WORKING_STORAGE_PATTERN.match(body):
                in_file_section = False

            if in_file_section:
                match = LEVEL_01_PATTERN.match(body)
                if match:
                    names.add(match.group("name").upper())

            match = RECORD_VERB_PATTERN.match(body)
            if match:
                names.add(match.group("name").upper())

            for pattern in (
                WRITE_FROM_PATTERN,
                READ_INTO_PATTERN,
                MOVE_WHOLE_GROUP_PATTERN,
            ):
                found = pattern.search(body)
                if found:
                    names.add(found.group("name").upper())

        return names

    def _logical(self, line: str) -> str:
        try:
            return str(self.fixed_format.logical(line) or "").strip()
        except Exception:  # noqa: BLE001
            return str(line or "").strip()

    @staticmethod
    def _is_comment(body: str) -> bool:
        return body.startswith(COMMENT_PREFIXES)


__all__ = [
    "WorkingStorageGroup",
    "WorkingStorageLayout",
    "WorkingStorageGroupSelector",
]