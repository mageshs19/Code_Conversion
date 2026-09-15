# LOCATION: src/idms_db2_phase2/composers/counter_declaration_composer.py
# ACTION: CREATE NEW FILE

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

Placement
---------
Counters are declared as subordinates of the FIRST 01 group in
WORKING-STORAGE, at the same level as that group's existing children.
The manual reference puts them inside 01 WS-TE-WORK at level 10; the
level is read from the program rather than assumed, so a site using 05
gets 05.

Clean Architecture
------------------
- Constants live in rules/counter_declaration_rules.py.
- Regex lives in patterns/counter_declaration_patterns.py.
- No program, record, table, cursor or host variable name is hardcoded.
"""

from __future__ import annotations

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from patterns.counter_declaration_patterns import (
    COUNTER_INCREMENT_PATTERN,
    DATA_ENTRY_PATTERN,
    GROUP_HEADER_PATTERN,
    SECTION_OR_DIVISION_PATTERN,
    STOP_RUN_PATTERN,
    SUBORDINATE_ENTRY_PATTERN,
    WORKING_STORAGE_PATTERN,
)
from rules.counter_declaration_rules import (
    COUNTER_DECLARATION_MESSAGES,
    COUNTER_DECLARATION_TEMPLATE,
    COUNTER_DISPLAY_TEMPLATE,
    COUNTER_LABEL_TEMPLATE,
    COUNTER_LABEL_WIDTH,
    COUNTER_PICTURE,
    EMIT_COUNTER_TOTALS,
    ENFORCE_COUNTER_DECLARATION,
    FALLBACK_CHILD_LEVEL,
    TOTALS_ANCHOR_STATEMENT,
    TOTALS_INDENT,
)

COUNTER_PREFIX = "WS-NB-"
COUNTER_SUFFIX = "-COUNT"
OUTPUT_TOKEN = "OUTPUT"


class CounterDeclarationComposer:
    """Declares referenced row counters and emits end-of-run totals."""

    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.fixed_format = fixed_format or FixedFormatLineService()
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
            lines = self._declare(lines, missing)

        if EMIT_COUNTER_TOTALS:
            lines = self._append_totals(lines, referenced)

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

    # =================================================================
    # Declaration
    # =================================================================
    def _declare(
        self,
        lines: list[str],
        missing: list[str],
    ) -> list[str]:
        anchor = self._group_anchor(lines)

        if anchor is None:
            self.messages.append(
                COUNTER_DECLARATION_MESSAGES["skipped_no_group"].format(
                    count=len(missing)
                )
            )
            return lines

        index, group_name, level = anchor
        template = lines[index]

        block: list[str] = []
        for name in missing:
            body = COUNTER_DECLARATION_TEMPLATE.format(
                level=level,
                name=name,
                picture=COUNTER_PICTURE,
            )
            block.append(self._clone(template, body))
            self.messages.append(
                COUNTER_DECLARATION_MESSAGES["declared"].format(
                    name=name,
                    group=group_name,
                )
            )

        return lines[: index + 1] + block + lines[index + 1 :]

    def _group_anchor(
        self,
        lines: list[str],
    ) -> tuple[int, str, str] | None:
        """(header index, group name, child level) of the first 01 group.

        Only WORKING-STORAGE is considered. The child level is taken from
        the group's first subordinate so a site using 05 is respected.
        """
        in_working_storage = False

        for index, line in enumerate(lines):
            if self.fixed_format.is_comment_or_control_line(line):
                continue

            logical = self.fixed_format.logical(line)
            if not logical:
                continue

            if WORKING_STORAGE_PATTERN.match(logical):
                in_working_storage = True
                continue

            if not in_working_storage:
                continue

            if SECTION_OR_DIVISION_PATTERN.match(logical):
                return None

            header = GROUP_HEADER_PATTERN.match(logical)
            if not header:
                continue

            level = self._child_level(lines, index)
            if level is None:
                continue

            return index, header.group("name").upper(), level

        return None

    def _child_level(self, lines: list[str], header_index: int) -> str | None:
        """Level number of the group's first subordinate entry."""
        for index in range(header_index + 1, len(lines)):
            line = lines[index]

            if self.fixed_format.is_comment_or_control_line(line):
                continue

            logical = self.fixed_format.logical(line)
            if not logical:
                continue

            if GROUP_HEADER_PATTERN.match(logical):
                return None

            if SECTION_OR_DIVISION_PATTERN.match(logical):
                return None

            match = SUBORDINATE_ENTRY_PATTERN.match(logical)
            if match:
                return match.group("level")

            return FALLBACK_CHILD_LEVEL

        return None

    # =================================================================
    # End-of-run totals
    # =================================================================
    def _append_totals(
        self,
        lines: list[str],
        counters: list[str],
    ) -> list[str]:
        anchor = self._stop_run_index(lines)

        if anchor < 0:
            self.messages.append(
                COUNTER_DECLARATION_MESSAGES["skipped_no_anchor"].format(
                    anchor=TOTALS_ANCHOR_STATEMENT
                )
            )
            return lines

        if self._totals_present(lines, counters):
            return lines

        template = lines[anchor]
        block: list[str] = []

        for name in self._ordered_for_display(counters):
            label = COUNTER_LABEL_TEMPLATE.format(
                token=self._token_of(name)
            ).ljust(COUNTER_LABEL_WIDTH)
            body = TOTALS_INDENT + COUNTER_DISPLAY_TEMPLATE.format(
                label=label,
                name=name,
            )
            block.append(self._clone(template, body))

        block.append(self._clone(template, ""))

        self.messages.append(
            COUNTER_DECLARATION_MESSAGES["totals_added"].format(
                count=len(block) - 1
            )
        )
        return lines[:anchor] + block + lines[anchor:]

    def _stop_run_index(self, lines: list[str]) -> int:
        for index, line in enumerate(lines):
            if self.fixed_format.is_comment_or_control_line(line):
                continue
            if STOP_RUN_PATTERN.match(self.fixed_format.logical(line)):
                return index
        return -1

    def _totals_present(
        self,
        lines: list[str],
        counters: list[str],
    ) -> bool:
        joined = " ".join(
            self.fixed_format.logical(line).upper() for line in lines
        )
        return all(f"DISPLAY" in joined and name in joined for name in counters) \
            and "TOTAL" in joined

    @staticmethod
    def _ordered_for_display(counters: list[str]) -> list[str]:
        """Fetch counters first, the output counter last."""
        output = [c for c in counters if c.upper().endswith(
            f"{COUNTER_PREFIX}{OUTPUT_TOKEN}{COUNTER_SUFFIX}".upper()
        )]
        others = [c for c in counters if c not in output]
        return others + output

    @staticmethod
    def _token_of(name: str) -> str:
        """WS-NB-OUTPUT-COUNT -> OUTPUT."""
        token = name.upper()
        if token.startswith(COUNTER_PREFIX):
            token = token[len(COUNTER_PREFIX):]
        if token.endswith(COUNTER_SUFFIX):
            token = token[: -len(COUNTER_SUFFIX)]
        return token or name

    # =================================================================
    # Helpers
    # =================================================================
    def _clone(self, template: str, body: str) -> str:
        """Build a line borrowing the sequence area of `template`.

        FinalSequenceResequencerService rewrites columns 1-6 and 73-80
        afterwards, so borrowed numbers are placeholders only.
        """
        left, indicator, _body, right = self.fixed_format.split(template)
        built = self.fixed_format.build_or_none(
            left, indicator or " ", body, right
        )
        return built if built is not None else body