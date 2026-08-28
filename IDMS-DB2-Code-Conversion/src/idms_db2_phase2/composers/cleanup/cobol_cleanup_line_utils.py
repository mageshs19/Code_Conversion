"""
COBOL cleanup line utilities.

Shared, stateless text helpers used by the COBOL cleanup helper classes.
Owns no regex and no business rules.
"""

from patterns.sequence_patterns import strip_sequence_numbers


class CobolCleanupLineUtils:
    def logical(self, line: str) -> str:
        return strip_sequence_numbers(str(line or "")).strip()

    def leading_spaces(self, line: str) -> str:
        value = str(line or "")
        return value[: len(value) - len(value.lstrip())]

    def is_comment_or_blank(self, logical: str) -> bool:
        stripped = str(logical or "").strip()

        if not stripped:
            return True

        return stripped.startswith("*") or stripped.startswith("/")