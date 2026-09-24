# LOCATION: src/idms_db2_phase2/composers/cursor_close_guarantee/line_utils.py
# ACTION: CREATE NEW FILE

"""Line inspection and formatting helpers.

Wraps CursorFlowLineFormatter so every helper in this package shares one
formatter instance and therefore one definition of "logical line" and one
definition of "format like this reference line".

Owns no regex definitions beyond what it imports, and no business rules.
"""

from __future__ import annotations

from idms_db2_phase2.composers.cursor_flow_line_formatter import (
    CursorFlowLineFormatter,
)
from patterns.cursor_close_guarantee_patterns import UNTIL_ONLY_PATTERN
from rules.cursor_close_guarantee_rules import (
    LEGACY_EOC_CONDITIONS,
    STATEMENT_TERMINATOR,
)

COMMENT_INDICATORS = ("*", "/")
UNTIL_KEYWORD = "UNTIL"


class CursorGuaranteeLineUtils:
    """Physical line helpers shared by every close-guarantee helper."""

    def __init__(
        self,
        line_formatter: CursorFlowLineFormatter | None = None,
    ) -> None:
        self.line_formatter = line_formatter or CursorFlowLineFormatter()

    #
    # Reading
    #
    def logical(self, line: str) -> str:
        """The COBOL body of a line, sequence areas stripped."""
        return self.line_formatter.logical(line)

    def is_blank_or_comment(self, line: str) -> bool:
        logical = self.logical(line)
        return not logical or self.is_comment(logical)

    @staticmethod
    def is_comment(logical: str) -> bool:
        text = str(logical or "").strip()
        return bool(text) and text[0] in COMMENT_INDICATORS

    @staticmethod
    def is_terminated(logical: str) -> bool:
        return str(logical or "").rstrip().endswith(STATEMENT_TERMINATOR)

    #
    # Writing
    #
    def format_like(self, reference_line: str, body: str) -> str:
        """Render `body` with the layout of `reference_line`."""
        return self.line_formatter.format_like_line(
            reference_line=reference_line,
            replacement_body=body,
        )

    #
    # Condition helpers
    #
    @staticmethod
    def partition_until(logical: str) -> tuple[str, str, str]:
        """Split a logical line on UNTIL, preserving the original case.

        Returns (head, keyword, tail). `keyword` is empty when the line
        carries no UNTIL clause.
        """
        text = str(logical or "")
        position = text.upper().find(UNTIL_KEYWORD)

        if position < 0:
            return text, "", ""

        head = text[:position]
        tail = text[position + len(UNTIL_KEYWORD) :].strip()

        return head, UNTIL_KEYWORD, tail

    @staticmethod
    def is_until_only(logical: str) -> bool:
        """True when the line carries nothing but the UNTIL clause."""
        return bool(UNTIL_ONLY_PATTERN.match(str(logical or "")))

    def is_legacy_condition(self, condition: str) -> bool:
        """True when the exit test is still the raw IDMS / SQLCODE form."""
        current = self.compress(condition)

        if not current:
            return False

        return any(
            current == self.compress(candidate)
            for candidate in LEGACY_EOC_CONDITIONS
        )

    #
    # Text helpers
    #
    @staticmethod
    def compress(text: str) -> str:
        """Whitespace-insensitive, case-insensitive comparison key."""
        return " ".join(str(text or "").split()).upper()

    @staticmethod
    def normalize_line_endings(text: str) -> str:
        return str(text or "").replace("\r\n", "\n").replace("\r", "\n")


__all__ = ["COMMENT_INDICATORS", "UNTIL_KEYWORD", "CursorGuaranteeLineUtils"]