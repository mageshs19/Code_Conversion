# LOCATION: src/idms_db2_phase2/composers/output_write/output_write_line_utils.py
# ACTION: CREATE NEW FILE
"""Line inspection and cloning for the output write extraction.

Two text views are deliberately distinct:

    logical(line)    UPPERCASED - for pattern matching only
    body_text(line)  ORIGINAL case - for text that is written back

Mixing them would upper-case business COBOL, which the business-flow
rule forbids.
"""

from __future__ import annotations

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from patterns.output_write_paragraph_patterns import (
    DIVISION_PATTERN,
    PARAGRAPH_HEADER_PATTERN,
)
from rules.output_write_paragraph_rules import (
    IND_STATEMENT,
    SCOPE_TERMINATOR_WORDS,
)

END_SCOPE_PREFIX = "END-"


class OutputWriteLineUtils:
    """Shared line helpers. Owns no business decision."""

    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.fixed_format = fixed_format or FixedFormatLineService()

    # ------------------------------------------------------ text views
    def logical(self, line: str) -> str:
        """Uppercased logical line. Matching only."""
        return self.fixed_format.logical(line).upper()

    def body_text(self, line: str) -> str:
        """Logical line in its ORIGINAL case. Rewriting only."""
        return self.fixed_format.logical(line)

    def is_skippable(self, line: str) -> bool:
        return self.fixed_format.is_comment_or_control_line(line)

    def body_indent(self, line: str) -> str:
        return self.fixed_format.body_indent(line)

    # ------------------------------------------------------ selection
    def executable_lines(self, body: list[str]) -> list[str]:
        return [
            line for line in body
            if self.body_text(line) and not self.is_skippable(line)
        ]

    def last_executable_index(self, body: list[str]) -> int:
        for index in range(len(body) - 1, -1, -1):
            line = body[index]
            if self.is_skippable(line):
                continue
            if self.body_text(line):
                return index
        return -1

    # ------------------------------------------------------ structure
    def paragraph_name(self, line: str) -> str:
        if self.is_skippable(line):
            return ""

        match = PARAGRAPH_HEADER_PATTERN.match(self.logical(line))
        if not match:
            return ""

        name = match.group("name").upper()
        if name in SCOPE_TERMINATOR_WORDS or name.startswith(
            END_SCOPE_PREFIX
        ):
            return ""

        return name

    def paragraph_names(self, lines: list[str]) -> set[str]:
        return {
            name for name in (self.paragraph_name(line) for line in lines)
            if name
        }

    @staticmethod
    def is_division_boundary(logical: str) -> bool:
        return bool(DIVISION_PATTERN.match(logical))

    # -------------------------------------------------------- building
    @staticmethod
    def template_line(lines: list[str], index: int) -> str:
        return lines[index] if 0 <= index < len(lines) else ""

    def clone(
        self,
        template: str,
        body: str,
        indicator: str | None = None,
    ) -> str:
        """Build a line borrowing the sequence area of `template`.

        FinalSequenceResequencerService rewrites columns 1-6 and 73-80
        afterwards, so borrowed numbers are placeholders only.
        """
        left, template_indicator, _body, right = self.fixed_format.split(
            template
        )
        marker = (
            indicator if indicator is not None
            else (template_indicator or " ")
        )
        built = self.fixed_format.build_or_none(left, marker, body, right)
        return built if built is not None else body

    def replace_body_wrapped(self, line: str, body: str) -> list[str]:
        return self.fixed_format.replace_body_wrapped(line, body)

    def call_indent(self, lines: list[str], body_start: int) -> str:
        for index in range(body_start, len(lines)):
            line = lines[index]
            if self.is_skippable(line):
                continue
            if self.body_text(line):
                return self.body_indent(line)
        return IND_STATEMENT


__all__ = ["OutputWriteLineUtils"]