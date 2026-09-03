from __future__ import annotations

from patterns.fixed_format_patterns import (
    COBOL_IDENTIFIER_TOKEN_PATTERN,
    RIGHT_SEQUENCE_WITH_SPACES_PATTERN,
    TRAILING_TIGHT_RIGHT_SEQUENCE_PATTERN,
    TRUE_LEFT_SEQUENCE_PATTERN,
)
from rules.fixed_format_rules import (
    COBOL_STATEMENT_STARTERS,
    RIGHT_SEQUENCE_GENERATED_PREFIX,
    TOTAL_WIDTH,
)


class FixedFormatSequenceStripper:
    """Strips loose left/right sequence numbers from non-fixed COBOL lines.

    Owns no regex definitions (patterns live in
    patterns/fixed_format_patterns.py) and no layout constants (rules).
    """

    def remove_loose_sequence_numbers(self, line: str) -> str:
        text = str(line or "").rstrip()
        text = self.remove_loose_right_sequence(text)
        text = self.remove_loose_left_sequence(text)
        return text.rstrip()

    def remove_loose_left_sequence(self, line: str) -> str:
        text = str(line or "")
        match = TRUE_LEFT_SEQUENCE_PATTERN.match(text)
        if not match:
            return text

        left = str(match.group("left") or "")
        body = str(match.group("body") or "")
        if not left.isdigit() or len(left) != 6:
            return text
        return body.lstrip()

    def remove_loose_right_sequence(self, line: str) -> str:
        text = str(line or "").rstrip()

        spaced = RIGHT_SEQUENCE_WITH_SPACES_PATTERN.match(text)
        if spaced:
            body = str(spaced.group("body") or "").rstrip()
            spaces = str(spaced.group("spaces") or "")
            right = str(spaced.group("right") or "")
            if self._looks_like_spaced_right_sequence(
                body=body, spaces=spaces, right=right, original=text
            ):
                return body

        tight = TRAILING_TIGHT_RIGHT_SEQUENCE_PATTERN.match(text)
        if tight:
            body = str(tight.group("body") or "").rstrip()
            right = str(tight.group("right") or "")
            if self._looks_like_tight_right_sequence(
                body=body, right=right, original=text
            ):
                return body

        return text

    def _looks_like_spaced_right_sequence(
        self, body: str, spaces: str, right: str, original: str
    ) -> bool:
        if not self._is_eight_digit_sequence(right):
            return False
        if not body:
            return False
        if len(original) >= TOTAL_WIDTH:
            return True
        if len(spaces) >= 2:
            return True
        return False

    def _looks_like_tight_right_sequence(
        self, body: str, right: str, original: str
    ) -> bool:
        if not self._is_eight_digit_sequence(right):
            return False
        if not body:
            return False
        if len(original) >= TOTAL_WIDTH and original[72:80].isdigit():
            return True

        body_upper = body.strip().upper()
        if not body_upper:
            return False
        if body_upper.startswith(COBOL_STATEMENT_STARTERS):
            return True
        if right.startswith(
            RIGHT_SEQUENCE_GENERATED_PREFIX
        ) and self._body_ends_like_cobol_identifier(body):
            return True
        return False

    def _is_eight_digit_sequence(self, value: str) -> bool:
        text = str(value or "")
        return len(text) == 8 and text.isdigit()

    def _body_ends_like_cobol_identifier(self, body: str) -> bool:
        text = str(body or "").rstrip()
        if not text:
            return False
        if text[-1].isdigit():
            return False
        if text[-1] in {"'", '"'}:
            return False
        last_token = text.split()[-1]
        return bool(COBOL_IDENTIFIER_TOKEN_PATTERN.fullmatch(last_token))