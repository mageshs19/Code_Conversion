# LOCATION: src/idms_db2_phase2/composers/counter_declaration/counter_anchor.py
# ACTION: CREATE NEW FILE
"""The place a counter declaration will be written.

CORRECTION - level number landed in Area A
------------------------------------------
The anchor previously cloned the 01 HEADER. A header sits in Area A with
a body indent of 0, so the generated line read

    10  WS-NB-OUTPUT-COUNT

at column 8 while every sibling sat at column 12. CHK-06.05 flagged it.

The template is now the group's FIRST SUBORDINATE entry, so the level
number AND the indent are both inherited from a real sibling.
"""

from __future__ import annotations

from dataclasses import dataclass

from idms_db2_phase2.composers.counter_declaration.counter_line_factory import (
    CounterLineFactory,
)
from patterns.counter_declaration_patterns import (
    GROUP_HEADER_PATTERN,
    SECTION_OR_DIVISION_PATTERN,
    SUBORDINATE_ENTRY_PATTERN,
)


@dataclass(frozen=True)
class CounterAnchor:
    """Where and how a counter declaration is rendered."""

    insert_index: int = -1
    template_line: str = ""
    level: str = ""
    indent: str = ""
    group: str = ""

    @property
    def is_usable(self) -> bool:
        return self.insert_index >= 0 and bool(self.level)


class CounterAnchorFinder:
    """Locates the first subordinate entry of an 01 group."""

    def __init__(
        self,
        line_factory: CounterLineFactory | None = None,
    ) -> None:
        self.lines = line_factory or CounterLineFactory()

    def first_child(
        self,
        lines: list[str],
        header_index: int,
    ) -> tuple[int, str] | None:
        """(index, level) of the group's first subordinate entry.

        Returns None when the group is empty, or when the next
        declaration belongs to another group or another section.
        """
        for index in range(header_index + 1, len(lines)):
            line = lines[index]

            if self.lines.is_skippable(line):
                continue

            logical = self.lines.logical(line)
            if not logical:
                continue

            if GROUP_HEADER_PATTERN.match(logical):
                return None

            if SECTION_OR_DIVISION_PATTERN.match(logical):
                return None

            match = SUBORDINATE_ENTRY_PATTERN.match(logical)
            if match:
                return index, match.group("level")

            return None

        return None

    def anchor_for(
        self,
        lines: list[str],
        header_index: int,
        group_name: str,
    ) -> CounterAnchor | None:
        child = self.first_child(lines, header_index)
        if child is None:
            return None

        child_index, level = child
        template = lines[child_index]

        return CounterAnchor(
            insert_index=header_index + 1,
            template_line=template,
            level=level,
            indent=self.lines.body_indent(template),
            group=group_name,
        )


__all__ = ["CounterAnchor", "CounterAnchorFinder"]