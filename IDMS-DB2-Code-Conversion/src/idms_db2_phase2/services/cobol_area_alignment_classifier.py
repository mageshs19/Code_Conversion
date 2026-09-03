"""
COBOL Area A / Area B alignment classification helpers.

This module contains decision helpers only. It does not rewrite COBOL lines.
"""

from __future__ import annotations

from patterns.final_feedback_fix_patterns import (
    DIVISION_SECTION_HEADER_PATTERN,
    PARAGRAPH_HEADER_PATTERN,
)
from rules.cobol_statement_rules import NON_PARAGRAPH_SINGLE_WORDS


class CobolAreaAlignmentClassifier:
    """
    Classifies Procedure Division logical lines for safe Area A / continuation
    decisions.
    """

    def is_area_a(
        self,
        logical: str,
    ) -> bool:
        text = str(logical or "").strip()
        upper = text.upper()

        if not text:
            return False

        if DIVISION_SECTION_HEADER_PATTERN.match(text):
            return True

        if not PARAGRAPH_HEADER_PATTERN.match(text):
            return False

        statement_name = upper.rstrip(".")

        if statement_name in NON_PARAGRAPH_SINGLE_WORDS:
            return False

        return True

    def looks_like_continuation(
        self,
        *,
        current_logical: str,
        next_logical: str,
    ) -> bool:
        """
        Detect generic continuation lines.

        This deliberately avoids hardcoded field/cursor names.

        Continuation is likely when:
        - current line ends with an operator or boolean connector
        - next line starts with a literal
        - next line starts with a comparison operand, not a COBOL verb/header
        """

        current = str(current_logical or "").strip().upper()
        next_text = str(next_logical or "").strip()
        next_upper = next_text.upper()

        if not current or not next_text:
            return False

        if current.endswith(("=", ">", "<", ">=", "<=", "OR", "AND", "NOT")):
            return True

        if next_text.startswith(("'", '"')):
            return True

        first_word = next_upper.split()[0] if next_upper.split() else ""

        if first_word in NON_PARAGRAPH_SINGLE_WORDS:
            return False

        if DIVISION_SECTION_HEADER_PATTERN.match(next_text):
            return False

        if PARAGRAPH_HEADER_PATTERN.match(next_text):
            return False

        return True