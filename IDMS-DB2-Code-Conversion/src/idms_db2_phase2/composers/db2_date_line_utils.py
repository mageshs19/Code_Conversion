"""
DB2 date line utilities.

Shared, stateless helpers used by the DB2 date comparison composer and its
collaborating classes. This module owns no regex and no business rules; it
only performs safe text-level operations.
"""

from patterns.sequence_patterns import strip_sequence_numbers


class Db2DateLineUtils:
    def normalize_line_endings(self, text: str) -> str:
        return str(text or "").replace("\r\n", "\n").replace("\r", "\n")

    def logical(self, line: str) -> str:
        return strip_sequence_numbers(str(line or "")).strip()

    def is_comment_or_blank(self, logical: str) -> bool:
        stripped = str(logical or "").strip()

        if not stripped:
            return True

        return stripped.startswith("*") or stripped.startswith("/")

    def leading_spaces_from_line(
        self,
        line: str,
        default: str = "",
    ) -> str:
        value = str(line or "")

        if not value:
            return default

        count = len(value) - len(value.lstrip(" "))

        if count <= 0:
            return default

        return value[:count]

    def clean_cobol_name(self, value: str) -> str:
        text = str(value or "").strip().upper()
        text = text.replace("_", "-")
        text = text.rstrip(".")

        while " " in text:
            text = text.replace(" ", "")

        return text

    def helper_name(self, field_name: str) -> str:
        return f"HELP-{self.clean_cobol_name(field_name)}"