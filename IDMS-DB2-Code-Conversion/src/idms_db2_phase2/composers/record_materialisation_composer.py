# LOCATION: src/idms_db2_phase2/composers/record_materialisation_composer.py
# ACTION: REPLACE ENTIRE FILE
"""Materialises IDMS records referenced by whole-record MOVE statements.

    MOVE VMBFAS TO F-FORM
        -> 05  F-FORM.
               06  VMBFAS.
                   07 ...
               06  FILLER             PIC X(46).
           MOVE <host> TO <field> OF VMBFAS   ... one per mapped field

CORRECTION E - first-match-wins (the defect that masked all the others)

    find_move returned the FIRST whole-record MOVE and compose() ran
    'return str(text)' on any refusal, abandoning the entire pass. A
    LINKAGE date field (DATE8-LS) matched first, had no Sheet Mapping
    rows, and VMBFAS was never examined - it then reached the structural
    safety pass and was commented out.

    Every whole-record MOVE is now visited, and a refusal is LOCAL.

CORRECTION F - a refusal was invisible

    Each refusal already carried its reason, but the reason landed in
    the Info band among thirty-odd other lines, so several runs went by
    with nobody able to say WHY the record did not materialise.

    Three changes close that:

      * the measured target length is reported on every attempt, so a
        length refusal needs no code read to interpret,
      * every refusal reason is collected and re-emitted as ONE summary
        line naming the records,
      * rules/validation_display_rules.py lifts refusal wording into the
        Warnings band.

Orchestration only:

    record_move_scanner.py               finds the sites
    record_materialisation_guard.py      decides refusals
    record_block_writer.py               writes the replacement lines
"""

from __future__ import annotations

from idms_db2_phase2.composers.record_materialisation.record_block_writer import (
    RecordBlockWriter,
)
from idms_db2_phase2.composers.record_materialisation.record_layout_generator import (
    RecordLayoutGenerator,
)
from idms_db2_phase2.composers.record_materialisation.record_line_utils import (
    RecordLineUtils,
)
from idms_db2_phase2.composers.record_materialisation.record_materialisation_guard import (
    RecordMaterialisationGuard,
)
from idms_db2_phase2.composers.record_materialisation.record_move_generator import (
    RecordMoveGenerator,
)
from idms_db2_phase2.composers.record_materialisation.record_move_scanner import (
    RecordMoveScanner,
)
from idms_db2_phase2.composers.record_materialisation.record_plan_builder import (
    RecordPlanBuilder,
)
from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from rules.record_materialisation_rules import (
    EMIT_TARGET_MEASUREMENT,
    ENFORCE_RECORD_MATERIALISATION,
    MAX_RECORD_MOVES,
    RECORD_MATERIALISATION_MESSAGES,
)

DETAIL_SEPARATOR = "; "
DETAIL_TEMPLATE = "{record} ({reason})"
MAX_DETAILS = 6


class RecordMaterialisationComposer:
    """Expands every whole-record MOVE it can prove safe."""

    def __init__(
        self,
        *,
        mapping_repository,
        table_name_resolver,
        host_variable_resolver,
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.lines = RecordLineUtils(
            fixed_format=fixed_format or FixedFormatLineService()
        )
        self.scanner = RecordMoveScanner(self.lines)
        self.guard = RecordMaterialisationGuard(
            plan_builder=RecordPlanBuilder(
                mapping_repository=mapping_repository,
                table_name_resolver=table_name_resolver,
                host_variable_resolver=host_variable_resolver,
            )
        )
        self.writer = RecordBlockWriter(
            layout_generator=RecordLayoutGenerator(),
            move_generator=RecordMoveGenerator(),
            line_utils=self.lines,
        )
        self.messages: list[str] = []
        self.refusals: list[tuple[str, str]] = []

    # =================================================================
    # Public entry point
    # =================================================================
    def compose(self, text: str) -> str:
        self.messages = []
        self.refusals = []

        if not text or not ENFORCE_RECORD_MATERIALISATION:
            return str(text or "")

        current = str(text).replace("\r\n", "\n").replace("\r", "\n")

        handled: set[tuple[str, str]] = set()
        examined = applied = 0

        for _ in range(MAX_RECORD_MOVES):
            source = current.split("\n")

            site = self.scanner.find_move(source, handled)
            if site is None:
                break

            handled.add(site.key)
            examined += 1

            rewritten = self._materialise(source, site)
            if rewritten is None:
                continue

            current = "\n".join(rewritten)
            applied += 1

        self._report(examined, applied)
        return current.rstrip() + "\n"

    # =================================================================
    # One record - None when refused
    # =================================================================
    def _materialise(self, lines: list[str], site) -> list[str] | None:
        plan, refusal = self.guard.build_plan(site.record)
        if refusal is not None:
            self._refuse(site.record, refusal)
            return None

        target = self.scanner.find_target(lines, site.target)

        if not target.is_found:
            self._refuse_key(
                site.record,
                "skipped_no_target",
                "target field not found in the DATA DIVISION",
                target=site.target,
            )
            return None

        # Two numbers that make a length refusal self-explanatory.
        if EMIT_TARGET_MEASUREMENT:
            self._log_key(
                "target_measured",
                target=site.target,
                bytes=target.declared_bytes,
                record=plan.record_name,
                actual=plan.total_bytes,
            )

        refusal = self.guard.check_length(
            plan, site.target, target.declared_bytes
        )
        if refusal is not None:
            self._refuse(site.record, refusal)
            return None

        advice = self.guard.check_movable(plan)
        if advice is not None:
            self._log(advice)

        updated = self.writer.replace_move(list(lines), site.index, plan)
        updated = self.writer.expand_target(
            updated,
            target.index,
            site.target,
            plan,
            target_level=target.level,
            declared_bytes=target.declared_bytes,
        )

        self._log_success(plan, site.target, target.declared_bytes)
        return updated

    # =================================================================
    # Diagnostics
    # =================================================================
    def _log_success(self, plan, target: str, declared_bytes: int) -> None:
        self._log_key(
            "materialised",
            target=target,
            record=plan.record_name,
            fields=len(plan.declarable_fields),
            bytes=plan.total_bytes,
            moves=len(plan.movable_fields),
        )

        # A target whose PIC could not be sized silently disables the
        # remainder FILLER, so the record shortens and every following
        # byte shifts. Never let that happen without a diagnostic.
        if not declared_bytes:
            self._log_key(
                "no_declared_length",
                target=target,
                record=plan.record_name,
            )
            return

        remainder = plan.remainder_bytes(declared_bytes)
        if remainder:
            self._log_key(
                "remainder_filler",
                record=plan.record_name,
                target=target,
                actual=plan.total_bytes,
                expected=declared_bytes,
                remainder=remainder,
            )

    def _report(self, examined: int, applied: int) -> None:
        """A no-op is always visible, and a refusal is never buried."""
        if examined == 0:
            self._log_key("no_moves")
            return

        self._log_key(
            "scan_summary",
            examined=examined,
            applied=applied,
            refused=len(self.refusals),
        )

        if not self.refusals:
            return

        details = DETAIL_SEPARATOR.join(
            DETAIL_TEMPLATE.format(record=record, reason=reason)
            for record, reason in self.refusals[:MAX_DETAILS]
        )
        self._log_key(
            "refusal_summary",
            count=len(self.refusals),
            details=details,
        )

    # =================================================================
    # Refusal recording
    # =================================================================
    def _refuse(self, record: str, refusal) -> None:
        """Log the reason AND remember it for the summary line."""
        self._log(refusal)
        self.refusals.append((record, self._reason_of(refusal)))

    def _refuse_key(
        self,
        record: str,
        key: str,
        reason: str,
        **values,
    ) -> None:
        self._log_key(key, **values)
        self.refusals.append((record, reason))

    @staticmethod
    def _reason_of(refusal) -> str:
        """A short human reason, derived from the message key."""
        return str(getattr(refusal, "key", "") or "refused").replace(
            "skipped_", ""
        ).replace("_", " ")

    # =================================================================
    # Message rendering
    # =================================================================
    def _log(self, refusal) -> None:
        values = dict(getattr(refusal, "values", {}) or {})
        self._log_key(getattr(refusal, "key", ""), **values)

    def _log_key(self, key: str, **values) -> None:
        template = RECORD_MATERIALISATION_MESSAGES.get(key, "")
        if not template:
            return
        try:
            self.messages.append(template.format(**values))
        except (IndexError, KeyError):
            # A template/value mismatch must never lose the diagnostic.
            self.messages.append(f"{template} [{key}: {values}]")


__all__ = ["RecordMaterialisationComposer"]