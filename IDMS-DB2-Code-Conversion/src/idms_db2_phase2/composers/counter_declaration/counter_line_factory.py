# LOCATION: src/idms_db2_phase2/composers/counter_declaration/counter_line_factory.py
# ACTION: CREATE NEW FILE
"""Fixed-format line rendering for generated counter lines.

Owns no rules and no regex. Every generated line borrows the sequence
area of a template line; FinalSequenceResequencerService rewrites
columns 1-6 and 73-80 afterwards, so borrowed numbers are placeholders.
"""

from __future__ import annotations

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)

FALLBACK_COMMENT_PREFIX = "      *"


class CounterLineFactory:
    """Builds statement, comment and blank lines from a template."""

    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.fixed_format = fixed_format or FixedFormatLineService()

    # ---------------------------------------------------------- public
    def statement(self, template: str, body: str) -> str:
        """An executable line carrying `body` in columns 8-72."""
        left, indicator, _body, right = self.fixed_format.split(template)
        built = self.fixed_format.build_or_none(
            left,
            indicator or " ",
            body,
            right,
        )
        return built if built is not None else body

    def comment(self, template: str, body: str) -> str:
        """A comment line: '*' in column 7, text from column 8."""
        left, _indicator, _body, right = self.fixed_format.split(template)
        text = str(body or "").lstrip("*").strip()
        built = self.fixed_format.build_or_none(left, "*", text, right)
        return built if built is not None else f"{FALLBACK_COMMENT_PREFIX}{text}"

    def blank(self, template: str) -> str:
        return self.statement(template, "")

    def body_indent(self, template: str) -> str:
        """Leading spaces of the template's body, as a string."""
        try:
            return self.fixed_format.body_indent(template)
        except Exception:  # noqa: BLE001
            return ""

    def logical(self, line: str) -> str:
        try:
            return str(self.fixed_format.logical(line) or "").strip()
        except Exception:  # noqa: BLE001
            return str(line or "").strip()

    def is_skippable(self, line: str) -> bool:
        """Comment, page-eject, debug or continuation line."""
        try:
            return bool(self.fixed_format.is_comment_or_control_line(line))
        except Exception:  # noqa: BLE001
            return False


__all__ = ["CounterLineFactory"]