# LOCATION: src/idms_db2_phase2/composers/counter_declaration_composer.py
# ACTION: REPLACE ENTIRE FILE

"""Counter declaration composer.

Declares every row counter the PROCEDURE DIVISION increments but
WORKING-STORAGE does not define, and appends the end-of-run totals.

Why this exists
---------------
OutputWriteParagraphComposer emits

    ADD 1 TO WS-NB-OUTPUT-COUNT

at the write call site, matching the manual reference. Nothing declared
the field, so the generated program did not compile.

Reference-driven, not table-driven
----------------------------------
The composer collects the counters actually referenced, subtracts the
names already declared anywhere in the DATA DIVISION, and declares only
the remainder. It therefore cannot declare an unused field, and cannot
miss one that a later generator starts incrementing.

Responsibility split
--------------------
This class decides WHAT to declare. CounterDeclarationWriter decides
WHERE to put it, which is where the record-corruption defect lived.

Clean Architecture
------------------
- Constants live in rules/counter_declaration_rules.py and
  rules/structural_safety_rules.py.
- Regex lives in patterns/counter_declaration_patterns.py.
- No program, record, table, cursor or host variable name is hardcoded.
"""

from __future__ import annotations

from idms_db2_phase2.composers.counter_declaration_writer import (
    CounterDeclarationWriter,
)
from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from patterns.counter_declaration_patterns import (
    COUNTER_INCREMENT_PATTERN,
    DATA_ENTRY_PATTERN,
)
from rules.counter_declaration_rules import (
    EMIT_COUNTER_TOTALS,
    ENFORCE_COUNTER_DECLARATION,
)


class CounterDeclarationComposer:
    """Declares referenced row counters and emits end-of-run totals."""

    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
        writer: CounterDeclarationWriter | None = None,
    ) -> None:
        self.fixed_format = fixed_format or FixedFormatLineService()
        self.writer = writer or CounterDeclarationWriter(
            fixed_format=self.fixed_format,
        )
        self.messages: list[str] = []

    # =================================================================
    # Public entry point
    # =================================================================
    def compose(self, text: str) -> str:
        self.messages = []

        if not text or not ENFORCE_COUNTER_DECLARATION:
            return str(text or "")

        lines = (
            str(text)
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .split("\n")
        )

        referenced = self._referenced_counters(lines)
        if not referenced:
            return "\n".join(lines).rstrip() + "\n"

        declared = self._declared_names(lines)
        missing = [name for name in referenced if name not in declared]

        if missing:
            lines = self.writer.declare(lines=lines, missing=missing)
            self.messages.extend(self.writer.messages)

        if EMIT_COUNTER_TOTALS:
            lines = self.writer.append_totals(
                lines=lines,
                counters=referenced,
            )
            self.messages.extend(self.writer.messages)

        return "\n".join(lines).rstrip() + "\n"

    # =================================================================
    # Collection
    # =================================================================
    def _referenced_counters(self, lines: list[str]) -> list[str]:
        """Counter names incremented anywhere in the program, in order."""
        out: list[str] = []
        seen: set[str] = set()

        for line in lines:
            if self.fixed_format.is_comment_or_control_line(line):
                continue

            match = COUNTER_INCREMENT_PATTERN.match(
                self.fixed_format.logical(line)
            )
            if not match:
                continue

            name = match.group("name").upper()
            if name not in seen:
                seen.add(name)
                out.append(name)

        return out

    def _declared_names(self, lines: list[str]) -> set[str]:
        """Every data name declared anywhere in the program."""
        out: set[str] = set()

        for line in lines:
            if self.fixed_format.is_comment_or_control_line(line):
                continue

            match = DATA_ENTRY_PATTERN.match(self.fixed_format.logical(line))
            if match:
                out.add(match.group("name").upper())

        return out


__all__ = ["CounterDeclarationComposer"]