# LOCATION: src/idms_db2_phase2/composers/cleanup/cobol_cleanup_line_utils.py
# ACTION: REPLACE ENTIRE FILE

"""Shared line helpers for the COBOL cleanup passes.

CORRECTION
----------
is_comment_or_blank() previously classified a line by inspecting the
STRIPPED text:

    return stripped.startswith("*") or stripped.startswith("/")

That only works when strip_sequence_numbers() has already removed the
left sequence number. When it had not - which was every comment and
page-eject line, because the old LEFT_SEQUENCE_PATTERN required
whitespace in the indicator column - a body such as "001690/" was
classified as EXECUTABLE COBOL and the terminator pass added a period.

Classification now reads column 7 of the RAW line, which is where the
COBOL standard puts the indicator, and never depends on stripping having
worked first.
"""

from __future__ import annotations

from patterns.sequence_patterns import (
    is_comment_or_control,
    is_fixed_format_line,
    is_sequence_artifact,
    strip_sequence_numbers,
)


class CobolCleanupLineUtils:
    """Line inspection helpers shared by every cleanup pass."""

    # -----------------------------------------------------------------
    # Text extraction
    # -----------------------------------------------------------------
    def logical(self, line: str) -> str:
        return strip_sequence_numbers(str(line or "")).strip()

    def leading_spaces(self, line: str) -> str:
        value = str(line or "")
        return value[: len(value) - len(value.lstrip())]

    # -----------------------------------------------------------------
    # Classification
    # -----------------------------------------------------------------
    def is_comment_or_blank(self, logical: str) -> bool:
        """Legacy signature: classify from already-stripped text.

        Retained because existing passes call it with self._logical(line).
        Prefer is_comment_or_blank_line(), which reads the raw line.
        """
        stripped = str(logical or "").strip()

        if not stripped:
            return True

        if stripped.startswith("*") or stripped.startswith("/"):
            return True

        # A leaked sequence number is not executable COBOL either. Without
        # this, the terminator pass punctuates it into '001690/.'.
        return bool(is_sequence_artifact(stripped))

    def is_comment_or_blank_line(self, line: str) -> bool:
        """Classify from the RAW line by reading column 7."""
        text = str(line or "").rstrip("\n")

        if not text.strip():
            return True

        if is_comment_or_control(text):
            return True

        return self.is_sequence_artifact(text)

    def is_fixed_line(self, line: str) -> bool:
        return is_fixed_format_line(line)

    def is_sequence_artifact(self, line: str) -> bool:
        return is_sequence_artifact(line)