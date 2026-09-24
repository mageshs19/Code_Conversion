# LOCATION: src/idms_db2_phase2/composers/counter_declaration/counter_anchor_resolver.py
# ACTION: CREATE NEW FILE
"""Safety-first placement for generated row counters.

CORRECTION - counter declared inside an output record
-----------------------------------------------------
Placement previously took the FIRST 01 group in WORKING-STORAGE. On a
program whose first group is the output record

    01  REC-FORM.
        05  F-FORM                PIC X(478).

that produced

    01  REC-FORM.
        05  WS-NB-OUTPUT-COUNT    PIC 9(7) COMP-3 VALUE ZEROES.
        05  F-FORM                PIC X(478).

shifting every byte of a fixed-length record. Every written record was
corrupted, silently.

Resolution order
----------------
1. reuse the generated counter group when a previous run made it,
2. otherwise reuse the LAST 01 group that is provably a work area,
3. otherwise create a dedicated 01 group at the WORKING-STORAGE boundary.

A record layout can never gain a field, in any branch.
"""

from __future__ import annotations

from idms_db2_phase2.composers.counter_declaration.counter_anchor import (
    CounterAnchor,
    CounterAnchorFinder,
)
from idms_db2_phase2.composers.counter_declaration.counter_line_factory import (
    CounterLineFactory,
)
from idms_db2_phase2.services.working_storage_group_selector import (
    WorkingStorageGroupSelector,
)
from rules.counter_declaration_rules import FALLBACK_CHILD_LEVEL
from rules.structural_safety_rules import (
    ENFORCE_SAFE_COUNTER_GROUP,
    GENERATED_COUNTER_CHILD_INDENT,
    GENERATED_COUNTER_GROUP_MARKER,
    GENERATED_COUNTER_GROUP_NAME,
    GENERATED_COUNTER_GROUP_TEMPLATE,
    PREFER_GENERATED_COUNTER_GROUP,
    STRUCTURAL_SAFETY_MESSAGES,
)

CREATED_GROUP_OFFSET = 3


class CounterAnchorResolver:
    """Chooses a safe anchor, creating a group when none is safe."""

    def __init__(
        self,
        line_factory: CounterLineFactory | None = None,
        selector: WorkingStorageGroupSelector | None = None,
        finder: CounterAnchorFinder | None = None,
    ) -> None:
        self.lines = line_factory or CounterLineFactory()
        self.selector = selector or WorkingStorageGroupSelector(
            fixed_format=self.lines.fixed_format,
        )
        self.finder = finder or CounterAnchorFinder(self.lines)
        self.messages: list[str] = []

    # ---------------------------------------------------------- public
    def resolve(
        self,
        lines: list[str],
    ) -> tuple[list[str], CounterAnchor | None]:
        self.messages = []
        layout = self.selector.analyze(lines)

        if not ENFORCE_SAFE_COUNTER_GROUP:
            group = layout.groups[0] if layout.groups else None
            if group is None:
                return lines, None
            return lines, self.finder.anchor_for(
                lines, group.header_index, group.name
            )

        anchor = self._reuse_generated_group(lines, layout)
        if anchor is not None:
            return lines, anchor

        # A business group such as 01 WS-DATUMS passes the record-layout
        # test but reads wrong: a row counter is not a date field. The
        # dedicated group is preferred unless the site opts out.
        if not PREFER_GENERATED_COUNTER_GROUP:
            anchor = self._reuse_safe_group(lines, layout)
            if anchor is not None:
                return lines, anchor

        self._report_rejected(layout)
        return self._create_group(lines, layout.boundary_index)
    
    # ------------------------------------------------------------ 1
    def _reuse_generated_group(self, lines, layout) -> CounterAnchor | None:
        for group in layout.groups:
            if group.name != GENERATED_COUNTER_GROUP_NAME:
                continue
            anchor = self.finder.anchor_for(
                lines, group.header_index, group.name
            )
            if anchor is not None:
                self._log("counter_group_reused", group=group.name)
                return anchor
        return None

    # ------------------------------------------------------------ 2
    def _reuse_safe_group(self, lines, layout) -> CounterAnchor | None:
        for group in reversed(layout.safe_groups()):
            anchor = self.finder.anchor_for(
                lines, group.header_index, group.name
            )
            if anchor is not None:
                self._log("counter_group_reused", group=group.name)
                return anchor
        return None

    # ------------------------------------------------------------ 3
    def _create_group(
        self,
        lines: list[str],
        boundary_index: int,
    ) -> tuple[list[str], CounterAnchor]:
        insert_at = boundary_index
        if insert_at < 0 or insert_at > len(lines):
            insert_at = len(lines)

        reference = lines[max(0, insert_at - 1)]
        marker = self.lines.comment(reference, GENERATED_COUNTER_GROUP_MARKER)
        header = self.lines.statement(
            reference,
            GENERATED_COUNTER_GROUP_TEMPLATE.format(
                name=GENERATED_COUNTER_GROUP_NAME,
            ),
        )

        updated = lines[:insert_at] + ["", marker, header] + lines[insert_at:]
        self._log("counter_group_created", group=GENERATED_COUNTER_GROUP_NAME)

        return updated, CounterAnchor(
            insert_index=insert_at + CREATED_GROUP_OFFSET,
            template_line=header,
            level=FALLBACK_CHILD_LEVEL,
            indent=GENERATED_COUNTER_CHILD_INDENT,
            group=GENERATED_COUNTER_GROUP_NAME,
        )

    # -------------------------------------------------------- helpers
    def _report_rejected(self, layout) -> None:
        for group in layout.groups:
            if group.is_record_layout:
                self._log("counter_group_rejected", group=group.name)

    def _log(self, key: str, **values) -> None:
        template = STRUCTURAL_SAFETY_MESSAGES.get(key, "")
        if template:
            self.messages.append(template.format(**values))


__all__ = ["CounterAnchorResolver"]