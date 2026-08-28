"""
Cursor flow line formatter.

Formats generated cursor-flow lines so they match the indentation and
fixed-format layout of a reference line. This helper owns no regex and no
business rules; it only performs safe physical formatting.
"""

from patterns.sequence_patterns import strip_sequence_numbers


class CursorFlowLineFormatter:
    FIXED_FORMAT_MIN_WIDTH = 80
    BODY_WIDTH = 65

    def logical(self, line: str) -> str:
        return strip_sequence_numbers(str(line or "")).strip()

    def normalize_line_endings(self, text: str) -> str:
        return str(text or "").replace("\r\n", "\n").replace("\r", "\n")

    def format_like_line(
        self,
        reference_line: str,
        replacement_body: str,
    ) -> str:
        line = str(reference_line or "").rstrip()

        if self._is_fixed_format_line(line):
            left = line[:6]
            indicator = line[6]
            right = line[72:80]
            body = self._body_with_reference_indent(
                reference_line=line,
                replacement_body=replacement_body,
            )
            return (
                f"{left}{indicator}"
                f"{body[: self.BODY_WIDTH].ljust(self.BODY_WIDTH)}"
                f"{right}"
            )

        indent = self.leading_spaces(reference_line, default="    ")
        return f"{indent}{replacement_body}"

    def _body_with_reference_indent(
        self,
        reference_line: str,
        replacement_body: str,
    ) -> str:
        body = reference_line[7:72].rstrip()
        indent = self.leading_spaces(body, default="    ")
        return f"{indent}{replacement_body}"

    def _is_fixed_format_line(self, line: str) -> bool:
        if len(line) < self.FIXED_FORMAT_MIN_WIDTH:
            return False
        if not line[:6].isdigit():
            return False
        if not line[72:80].isdigit():
            return False
        return True

    def leading_spaces(self, text: str, default: str = "") -> str:
        value = str(text or "")
        if not value:
            return default
        count = len(value) - len(value.lstrip(" "))
        if count <= 0:
            return default
        return value[:count]