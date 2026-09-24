# LOCATION: src/idms_db2_phase2/composers/counter_declaration/counter_totals_writer.py
# ACTION: CREATE NEW FILE
"""End-of-run counter totals.

CORRECTION - totals suppressed by an unrelated DISPLAY
------------------------------------------------------
The idempotency test was

    all(f"DISPLAY" in joined and name in joined for name in counters)

a placeholder-less f-string asking whether the word DISPLAY appeared
ANYWHERE in the program. One unrelated DISPLAY suppressed every total.

The test is now per counter, per line: a counter counts as already
displayed only when a single line carries DISPLAY, TOTAL and that
counter's name.
"""

from __future__ import annotations

from idms_db2_phase2.composers.counter_declaration.counter_line_factory import (
    CounterLineFactory,
)
from patterns.cobol_patterns import GOBACK_PATTERN, STOP_RUN_PATTERN
from rules.counter_declaration_rules import (
    COUNTER_DECLARATION_MESSAGES,
    COUNTER_DISPLAY_TEMPLATE,
    COUNTER_LABEL_TEMPLATE,
    COUNTER_LABEL_WIDTH,
    COUNTER_NAME_PREFIX,
    COUNTER_NAME_SUFFIX,
    COUNTER_OUTPUT_TOKEN,
    TOTALS_ANCHOR_STATEMENT,
    TOTALS_DISPLAY_VERB,
    TOTALS_INDENT,
    TOTALS_LABEL_TOKEN,
)


class CounterTotalsWriter:
    """Appends one DISPLAY per counter immediately before STOP RUN."""

    def __init__(
        self,
        line_factory: CounterLineFactory | None = None,
    ) -> None:
        self.lines = line_factory or CounterLineFactory()
        self.messages: list[str] = []

    # ---------------------------------------------------------- public
    def append(self, lines: list[str], counters: list[str]) -> list[str]:
        self.messages = []

        if not counters:
            return lines

        anchor = self._stop_run_index(lines)
        if anchor < 0:
            self.messages.append(
                COUNTER_DECLARATION_MESSAGES["skipped_no_anchor"].format(
                    anchor=TOTALS_ANCHOR_STATEMENT,
                )
            )
            return lines

        if self._already_present(lines, counters):
            return lines

        template = lines[anchor]
        block = [
            self.lines.statement(template, self._display_body(name))
            for name in self._ordered(counters)
        ]
        block.append(self.lines.blank(template))

        self.messages.append(
            COUNTER_DECLARATION_MESSAGES["totals_added"].format(
                count=len(block) - 1,
            )
        )
        return lines[:anchor] + block + lines[anchor:]

    # -------------------------------------------------------- helpers
    def _display_body(self, name: str) -> str:
        label = COUNTER_LABEL_TEMPLATE.format(
            token=self.token_of(name),
        ).ljust(COUNTER_LABEL_WIDTH)
        return TOTALS_INDENT + COUNTER_DISPLAY_TEMPLATE.format(
            label=label,
            name=name,
        )

    def _stop_run_index(self, lines: list[str]) -> int:
        """First program-termination statement: STOP RUN or GOBACK.

        CORRECTION - totals silently skipped.
        The anchor was STOP RUN only. A program CALLed with a parameter
        list ends with GOBACK, so every counter was declared and
        incremented but never displayed.
        """
        for index, line in enumerate(lines):
            if self.lines.is_skippable(line):
                continue

            logical = self.lines.logical(line)
            if STOP_RUN_PATTERN.match(logical):
                return index
            if GOBACK_PATTERN.match(logical):
                return index

        return -1
    
    def _already_present(
        self,
        lines: list[str],
        counters: list[str],
    ) -> bool:
        displayed: set[str] = set()

        for line in lines:
            if self.lines.is_skippable(line):
                continue

            logical = self.lines.logical(line).upper()
            if TOTALS_DISPLAY_VERB not in logical:
                continue
            if TOTALS_LABEL_TOKEN not in logical:
                continue

            for name in counters:
                if name.upper() in logical:
                    displayed.add(name.upper())

        return all(name.upper() in displayed for name in counters)

    @staticmethod
    def _ordered(counters: list[str]) -> list[str]:
        """Fetch counters first, the output counter last."""
        output_name = (
            f"{COUNTER_NAME_PREFIX}{COUNTER_OUTPUT_TOKEN}"
            f"{COUNTER_NAME_SUFFIX}"
        ).upper()
        output = [c for c in counters if c.upper() == output_name]
        others = [c for c in counters if c.upper() != output_name]
        return others + output

    @staticmethod
    def token_of(name: str) -> str:
        """WS-NB-OUTPUT-COUNT -> OUTPUT."""
        token = str(name or "").upper()
        if token.startswith(COUNTER_NAME_PREFIX):
            token = token[len(COUNTER_NAME_PREFIX):]
        if token.endswith(COUNTER_NAME_SUFFIX):
            token = token[: -len(COUNTER_NAME_SUFFIX)]
        return token or name


__all__ = ["CounterTotalsWriter"]