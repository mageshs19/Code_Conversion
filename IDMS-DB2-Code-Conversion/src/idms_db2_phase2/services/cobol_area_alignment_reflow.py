"""
COBOL Area B safe two-line reflow helper.

This module only handles long-line reflow using an existing continuation line.
It does not decide Procedure Division state or SQL state.
"""

from __future__ import annotations

from idms_db2_phase2.services.cobol_area_alignment_classifier import (
    CobolAreaAlignmentClassifier,
)
from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)

try:
    from rules.final_feedback_fix_rules import AREA_B_CONTINUATION_BODY_INDENT
except ImportError:
    AREA_B_CONTINUATION_BODY_INDENT = "       "


class CobolAreaAlignmentReflow:
    """
    Safely reflows long fixed-format Procedure Division statements into exactly
    two body lines, using the existing next line as continuation storage.
    """

    def __init__(
        self,
        *,
        fixed_format: FixedFormatLineService,
        classifier: CobolAreaAlignmentClassifier,
    ) -> None:
        self.fixed_format = fixed_format
        self.classifier = classifier

    def try_reflow_with_next_line(
        self,
        *,
        current_line: str,
        next_line: str,
        first_indent: str,
    ) -> list[str]:
        """
        Safely reflow a long fixed-format Procedure Division statement by using
        the existing next line as continuation storage.

        This method does not add new physical lines. It only rewrites the
        current line and the existing next line.
        """

        if not current_line or not next_line:
            return []

        if not self.fixed_format.is_fixed_line(current_line):
            return []

        if not self.fixed_format.is_fixed_line(next_line):
            return []

        current_logical = self.fixed_format.logical(current_line)
        next_logical = self.fixed_format.logical(next_line)

        if not current_logical or not next_logical:
            return []

        if self.fixed_format.is_comment_or_control_line(next_line):
            return []

        if self.classifier.is_area_a(next_logical):
            return []

        if not self.classifier.looks_like_continuation(
            current_logical=current_logical,
            next_logical=next_logical,
        ):
            return []

        combined = self.combine_logical_fragments(
            current_logical=current_logical,
            next_logical=next_logical,
        )

        if not combined:
            return []

        wrapped_bodies = self.wrap_into_two_bodies(
            logical=combined,
            first_indent=first_indent,
            continuation_indent=AREA_B_CONTINUATION_BODY_INDENT,
        )

        if len(wrapped_bodies) != 2:
            return []

        return [
            self.fixed_format.replace_body(current_line, wrapped_bodies[0]),
            self.fixed_format.replace_body(next_line, wrapped_bodies[1]),
        ]

    def combine_logical_fragments(
        self,
        *,
        current_logical: str,
        next_logical: str,
    ) -> str:
        current = str(current_logical or "").strip()
        continuation = str(next_logical or "").strip()

        if not current:
            return continuation

        if not continuation:
            return current

        return f"{current} {continuation}"

    def wrap_into_two_bodies(
        self,
        *,
        logical: str,
        first_indent: str,
        continuation_indent: str,
    ) -> list[str]:
        """
        Wrap one logical COBOL statement into exactly two body lines.

        Returns an empty list if the statement cannot be represented safely in
        two fixed-format body lines.
        """

        words = str(logical or "").split()

        if not words:
            return []

        first_limit = self.fixed_format.BODY_WIDTH - len(first_indent)
        second_limit = self.fixed_format.BODY_WIDTH - len(continuation_indent)

        if first_limit <= 0 or second_limit <= 0:
            return []

        first_words: list[str] = []

        for word in words:
            candidate = " ".join(first_words + [word])

            if len(candidate) <= first_limit:
                first_words.append(word)
                continue

            break

        first_word_count = len(first_words)
        second_words = words[first_word_count:]

        if not first_words or not second_words:
            return []

        second_text = " ".join(second_words)

        if len(second_text) > second_limit:
            return []

        first_body = first_indent + " ".join(first_words)
        second_body = continuation_indent + second_text

        if not self.body_fits(first_body):
            return []

        if not self.body_fits(second_body):
            return []

        return [first_body, second_body]

    def body_fits(
        self,
        body: str,
    ) -> bool:
        return len(str(body or "")) <= self.fixed_format.BODY_WIDTH