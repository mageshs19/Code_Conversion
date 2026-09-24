# LOCATION: src/idms_db2_phase2/composers/structural_safety_composer.py
# ACTION: REPLACE ENTIRE FILE
"""Final structural safety pass. COMMENT-ONLY, never deletes.

A2 - orphaned whole-record reference
    MOVE VMBFAS TO F-FORM survives after COPY IDMS LR is removed, so
    VMBFAS is an undefined data-name.

A4 - unreachable statement after a paragraph EXIT
    A statement between EXIT. and the next paragraph header can never
    run and sits outside any paragraph.

CORRECTION 1 - EXIT. matched the paragraph-header pattern
    The exit test now runs BEFORE the header test.

CORRECTION 2 - long markers lost their sequence numbers
    Comments are wrapped through emit().

CORRECTION 3 - comment lines were never recognised
    _is_comment() tested FixedFormatLineService.logical(), which returns
    columns 8-72 only. The '*' indicator lives in column 7, so it was
    never in the string being tested and every comment was treated as
    executable. Classification now reads the RAW line.

CORRECTION 4 - a tracking bug could comment out the whole program
    With CORRECTION 1 and 3 missing, the A4 guard stayed armed past the
    generated cursor block and commented 60+ lines. A hard cap now
    reverts the entire pass when it matches more lines than real
    unreachable code ever spans.
"""

from __future__ import annotations

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from patterns.structural_safety_patterns import (
    EXIT_STATEMENT_PATTERN,
    MOVE_BARE_SOURCE_PATTERN,
    MOVE_BARE_TARGET_PATTERN,
    PARAGRAPH_HEADER_PATTERN,
    PROCEDURE_DIVISION_PATTERN,
    QUALIFIER_PATTERN,
    SECTION_HEADER_PATTERN,
)
from rules.structural_safety_rules import (
    ENFORCE_ORPHANED_RECORD_GUARD,
    ENFORCE_UNREACHABLE_STATEMENT_GUARD,
    MAX_UNREACHABLE_STATEMENTS,
    ORPHANED_LINE_PREFIX,
    ORPHANED_RECORD_MARKER_TEMPLATE,
    STRUCTURAL_SAFETY_MESSAGES,
    UNREACHABLE_MARKER,
)

DCLGEN_PREFIX = "DCL"
FALLBACK_COMMENT_PREFIX = "      *"


class StructuralSafetyComposer:
    """Comments references the compiler would reject."""

    def __init__(
        self,
        original_idms_text: str = "",
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.original_idms_text = str(original_idms_text or "")
        self.fixed_format = fixed_format or FixedFormatLineService()
        self.messages: list[str] = []

    # ---------------------------------------------------------- public
    def compose(self, text: str) -> str:
        self.messages = []

        if not text:
            return ""

        lines = (
            str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n")
        )

        if ENFORCE_ORPHANED_RECORD_GUARD:
            lines = self._guard_orphaned_records(lines)

        if ENFORCE_UNREACHABLE_STATEMENT_GUARD:
            lines = self._guard_unreachable_statements(lines)

        return "\n".join(lines).rstrip() + "\n"

    # ------------------------------------------------------------- A2
    def _guard_orphaned_records(self, lines: list[str]) -> list[str]:
        records = self._idms_record_names()
        if not records:
            return lines

        declared = self._declared_names(lines)
        output: list[str] = []

        for line in lines:
            if self._is_skippable(line):
                output.append(line)
                continue

            body = self._logical(line)
            if not body:
                output.append(line)
                continue

            record = self._whole_record_reference(body, records, declared)
            if not record:
                output.append(line)
                continue

            output.extend(
                self._comment_lines(
                    line,
                    ORPHANED_RECORD_MARKER_TEMPLATE.format(record=record),
                )
            )
            output.extend(
                self._comment_lines(line, f"{ORPHANED_LINE_PREFIX}{body}")
            )
            self.messages.append(
                STRUCTURAL_SAFETY_MESSAGES[
                    "orphaned_record_commented"
                ].format(record=record)
            )

        return output

    def _idms_record_names(self) -> set[str]:
        names: set[str] = set()
        for match in QUALIFIER_PATTERN.finditer(self.original_idms_text):
            name = match.group("record").upper()
            if name and not name.startswith(DCLGEN_PREFIX):
                names.add(name)
        return names

    def _declared_names(self, lines: list[str]) -> set[str]:
        declared: set[str] = set()
        for line in lines:
            if self._is_skippable(line):
                continue
            body = self._logical(line)
            if not body:
                continue
            if PROCEDURE_DIVISION_PATTERN.match(body):
                break
            parts = body.split()
            if len(parts) >= 2 and parts[0].rstrip(".").isdigit():
                declared.add(parts[1].rstrip(".").upper())
        return declared

    @staticmethod
    def _whole_record_reference(
        body: str,
        records: set[str],
        declared: set[str],
    ) -> str:
        for pattern in (MOVE_BARE_SOURCE_PATTERN, MOVE_BARE_TARGET_PATTERN):
            match = pattern.match(body)
            if not match:
                continue
            name = match.group("name").upper()
            if name in records and name not in declared:
                return name
        return ""

    # ------------------------------------------------------------- A4
    def _guard_unreachable_statements(self, lines: list[str]) -> list[str]:
        output: list[str] = []
        after_exit = False
        in_procedure = False
        commented = 0

        for line in lines:
            # Comment, page-eject, debug and continuation lines are
            # classified from the RAW line: the indicator is column 7,
            # which logical() does not return.
            if self._is_skippable(line):
                output.append(line)
                continue

            body = self._logical(line)

            if PROCEDURE_DIVISION_PATTERN.match(body):
                in_procedure = True
                after_exit = False
                output.append(line)
                continue

            if not in_procedure or not body:
                output.append(line)
                continue

            # EXIT test FIRST: "EXIT." also matches the header pattern.
            if EXIT_STATEMENT_PATTERN.match(body):
                after_exit = True
                output.append(line)
                continue

            # Paragraph and section headers disarm the guard. The name
            # may start with a digit: 710-OPEN-<cursor>.
            if PARAGRAPH_HEADER_PATTERN.match(body) or (
                SECTION_HEADER_PATTERN.match(body)
            ):
                after_exit = False
                output.append(line)
                continue

            if not after_exit:
                output.append(line)
                continue

            output.extend(self._comment_lines(line, UNREACHABLE_MARKER))
            output.extend(
                self._comment_lines(line, f"{ORPHANED_LINE_PREFIX}{body}")
            )
            commented += 1

        # Blast-radius cap: revert everything rather than trust a guard
        # that has clearly lost sync with the paragraph structure.
        if commented > MAX_UNREACHABLE_STATEMENTS:
            self.messages.append(
                STRUCTURAL_SAFETY_MESSAGES["unreachable_aborted"].format(
                    count=commented,
                    limit=MAX_UNREACHABLE_STATEMENTS,
                )
            )
            return lines

        if commented:
            self.messages.append(
                STRUCTURAL_SAFETY_MESSAGES["unreachable_commented"].format(
                    count=commented,
                )
            )

        return output

    # -------------------------------------------------------- helpers
    def _comment_lines(self, reference: str, body: str) -> list[str]:
        """Comment line(s), wrapped when the text exceeds columns 8-72."""
        text = str(body or "").lstrip("*").strip()
        try:
            if self.fixed_format.is_fixed_line(reference):
                left, _ind, _old, right = self.fixed_format.split(reference)
                return self.fixed_format.emit(left, "*", text, right)
        except Exception:  # noqa: BLE001
            pass
        return [f"{FALLBACK_COMMENT_PREFIX}{text}"]

    def _logical(self, line: str) -> str:
        try:
            return str(self.fixed_format.logical(line) or "").strip()
        except Exception:  # noqa: BLE001
            return str(line or "").strip()

    def _is_skippable(self, line: str) -> bool:
        """Comment / page-eject / debug / continuation, read from column 7."""
        try:
            return bool(self.fixed_format.is_comment_or_control_line(line))
        except Exception:  # noqa: BLE001
            return str(line or "").lstrip().startswith(("*", "/"))


__all__ = ["StructuralSafetyComposer"]