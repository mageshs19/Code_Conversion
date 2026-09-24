# LOCATION: src/idms_db2_phase2/composers/counter_declaration_writer.py
# ACTION: REPLACE ENTIRE FILE
"""Facade over the counter declaration package.

Keeps a single import path for CounterDeclarationComposer while the
placement, rendering and totals logic lives in focused modules:

    counter_declaration/counter_line_factory.py     rendering
    counter_declaration/counter_anchor.py           anchor model + lookup
    counter_declaration/counter_anchor_resolver.py  safety-first placement
    counter_declaration/counter_totals_writer.py    end-of-run totals

This class contains no COBOL knowledge of its own.
"""

from __future__ import annotations

from idms_db2_phase2.composers.counter_declaration import (
    CounterAnchorResolver,
    CounterLineFactory,
    CounterTotalsWriter,
)
from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from rules.counter_declaration_rules import (
    COUNTER_DECLARATION_MESSAGES,
    COUNTER_DECLARATION_TEMPLATE,
    COUNTER_PICTURE,
)


class CounterDeclarationWriter:
    """Writes counter declarations and end-of-run totals."""

    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
        resolver: CounterAnchorResolver | None = None,
        totals_writer: CounterTotalsWriter | None = None,
    ) -> None:
        self.line_factory = CounterLineFactory(
            fixed_format=fixed_format or FixedFormatLineService(),
        )
        self.resolver = resolver or CounterAnchorResolver(
            line_factory=self.line_factory,
        )
        self.totals_writer = totals_writer or CounterTotalsWriter(
            line_factory=self.line_factory,
        )
        self.messages: list[str] = []

    # ---------------------------------------------------------- public
    def declare(self, lines: list[str], missing: list[str]) -> list[str]:
        self.messages = []

        if not missing:
            return lines

        lines, anchor = self.resolver.resolve(lines)
        self.messages.extend(self.resolver.messages)

        if anchor is None or not anchor.is_usable:
            self.messages.append(
                COUNTER_DECLARATION_MESSAGES["skipped_no_group"].format(
                    count=len(missing),
                )
            )
            return lines

        block: list[str] = []
        for name in missing:
            body = anchor.indent + COUNTER_DECLARATION_TEMPLATE.format(
                level=anchor.level,
                name=name,
                picture=COUNTER_PICTURE,
            )
            block.append(
                self.line_factory.statement(anchor.template_line, body)
            )
            self.messages.append(
                COUNTER_DECLARATION_MESSAGES["declared"].format(
                    name=name,
                    group=anchor.group,
                )
            )

        index = anchor.insert_index
        return lines[:index] + block + lines[index:]

    def append_totals(
        self,
        lines: list[str],
        counters: list[str],
    ) -> list[str]:
        self.messages = []
        lines = self.totals_writer.append(lines, counters)
        self.messages.extend(self.totals_writer.messages)
        return lines


__all__ = ["CounterDeclarationWriter"]