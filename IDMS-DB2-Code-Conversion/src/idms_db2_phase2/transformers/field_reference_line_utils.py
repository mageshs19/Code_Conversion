from __future__ import annotations

from patterns.field_reference_rewriter_patterns import (
    DCL_DOT_REFERENCE_PATTERN,
    HOST_OF_DCL_REFERENCE_PATTERN,
    STRING_PATTERN,
)


class FieldReferenceLineUtils:
    """
    Line-level helpers for field reference rewriting.

    This class does not access repositories or resolve DB2 metadata.
    """

    def logical_line(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()

        if len(text) >= 80:
            left = text[:6]
            indicator = text[6:7]
            body = text[7:72]

            if left.strip().isdigit():
                if indicator in {"*", "/"}:
                    return indicator + body.rstrip()

                return body.strip()

        if len(text) > 6 and text[:6].strip().isdigit():
            return text[6:].strip()

        return text.strip()

    def is_comment_or_blank(
        self,
        line: str,
    ) -> bool:
        logical = self.logical_line(line)
        stripped = str(logical or "").strip()

        if not stripped:
            return True

        if stripped.startswith("*"):
            return True

        if stripped.startswith("/"):
            return True

        return False

    def has_existing_dclgen_reference(
        self,
        line: str,
    ) -> bool:
        upper = str(line or "").upper()

        if " OF DCL" in upper:
            return True

        if DCL_DOT_REFERENCE_PATTERN.search(upper):
            return True

        if HOST_OF_DCL_REFERENCE_PATTERN.search(upper):
            return True

        return False

    def split_string_segments(
        self,
        line: str,
    ) -> list[tuple[str, bool]]:
        text = str(line or "")
        output: list[tuple[str, bool]] = []
        last_index = 0

        for match in STRING_PATTERN.finditer(text):
            if match.start() > last_index:
                output.append(
                    (
                        text[last_index : match.start()],
                        False,
                    )
                )

            output.append(
                (
                    match.group(0),
                    True,
                )
            )

            last_index = match.end()

        if last_index < len(text):
            output.append(
                (
                    text[last_index:],
                    False,
                )
            )

        return output