from __future__ import annotations

from patterns.cobol_transformer_patterns import (
    LEFT_SEQUENCE_PATTERN,
    RIGHT_SEQUENCE_PATTERN,
    RIGHT_SEQUENCE_WITH_SPACES_PATTERN,
)


class CobolTransformerLineUtils:
    """
    Handles COBOL logical line extraction and fixed-format body replacement.

    This utility preserves left and right sequence areas when replacing a
    logical COBOL body.
    """

    def logical_line(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()

        text = self.remove_right_sequence(text)
        text = self.remove_left_sequence(text)

        return text.strip()

    def remove_left_sequence(
        self,
        line: str,
    ) -> str:
        text = str(line or "")

        if len(text) >= 6 and text[:6].strip().isdigit():
            return text[6:].strip()

        return text

    def remove_right_sequence(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()
        match = RIGHT_SEQUENCE_PATTERN.match(text)

        if match:
            return match.group("body").rstrip()

        return text

    def replace_logical_body(
        self,
        original_line: str,
        replacement_body: str,
    ) -> str:
        text = str(original_line or "").rstrip()

        left_sequence = ""
        body_with_possible_right = text

        left_match = LEFT_SEQUENCE_PATTERN.match(body_with_possible_right)

        if left_match:
            left_sequence = left_match.group("left")
            body_with_possible_right = left_match.group("body")

        right_match = RIGHT_SEQUENCE_WITH_SPACES_PATTERN.match(
            body_with_possible_right
        )

        if right_match:
            original_body = right_match.group("body")
            original_spaces = right_match.group("spaces")
            right_sequence = right_match.group("right")

            original_body_area_width = len(original_body) + len(original_spaces)
            replacement = str(replacement_body or "")

            if len(replacement) >= original_body_area_width:
                formatted_body = replacement + " "
            else:
                formatted_body = replacement.ljust(original_body_area_width)

            return f"{left_sequence}{formatted_body}{right_sequence}"

        if left_sequence:
            return f"{left_sequence}{replacement_body}"

        return str(replacement_body or "")


__all__ = [
    "CobolTransformerLineUtils",
]