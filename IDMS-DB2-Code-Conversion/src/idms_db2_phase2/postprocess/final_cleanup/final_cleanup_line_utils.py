from __future__ import annotations

from patterns.update_final_cleanup_patterns import PARAGRAPH_HEADER_PATTERN
from rules.update_cobol_final_cleanup_rules import (
    FINAL_CLEANUP_BODY_END,
    FINAL_CLEANUP_BODY_START,
    FINAL_CLEANUP_BODY_WIDTH,
    FINAL_CLEANUP_COMMENT_CHARS,
    FINAL_CLEANUP_COMMENT_INDICATORS,
    FINAL_CLEANUP_DEBUG_PREFIX,
    FINAL_CLEANUP_FULL_WIDTH,
    FINAL_CLEANUP_INDICATOR_COLUMN,
    FINAL_CLEANUP_RIGHT_SEQUENCE_WIDTH,
    FINAL_CLEANUP_SEQUENCE_WIDTH,
    FINAL_CLEANUP_TOTAL_WIDTH,
)


class FinalCleanupLineUtils:
    """Fixed-format line helpers + paragraph range detection.

    Owns no business rules. Column geometry comes from
    rules/update_cobol_final_cleanup_rules.py.
    """

    def _replace_body(self, line: str, body: str) -> str:
        text = str(line or "").rstrip("\n")
        clean_body = str(body or "")[:FINAL_CLEANUP_BODY_WIDTH].ljust(
            FINAL_CLEANUP_BODY_WIDTH
        )

        if (
            len(text) >= FINAL_CLEANUP_FULL_WIDTH
            and text[:FINAL_CLEANUP_SEQUENCE_WIDTH].strip().isdigit()
        ):
            left = text[:FINAL_CLEANUP_SEQUENCE_WIDTH]
            right = (
                text[FINAL_CLEANUP_BODY_END:FINAL_CLEANUP_TOTAL_WIDTH]
                if len(text) >= FINAL_CLEANUP_TOTAL_WIDTH
                else ""
            )
            return f"{left} {clean_body} {right}"

        if (
            len(text) > FINAL_CLEANUP_SEQUENCE_WIDTH
            and text[:FINAL_CLEANUP_SEQUENCE_WIDTH].strip().isdigit()
        ):
            left = text[:FINAL_CLEANUP_SEQUENCE_WIDTH]
            return f"{left} {clean_body.rstrip()}"

        return clean_body.rstrip()

    def _body(self, line: str) -> str:
        text = str(line or "").rstrip("\n")

        if (
            len(text) >= FINAL_CLEANUP_FULL_WIDTH
            and text[:FINAL_CLEANUP_SEQUENCE_WIDTH].strip().isdigit()
        ):
            return text[FINAL_CLEANUP_BODY_START:FINAL_CLEANUP_BODY_END].rstrip()

        if (
            len(text) > FINAL_CLEANUP_SEQUENCE_WIDTH
            and text[:FINAL_CLEANUP_SEQUENCE_WIDTH].strip().isdigit()
        ):
            body = (
                text[FINAL_CLEANUP_BODY_START:]
                if len(text) > FINAL_CLEANUP_BODY_START
                else ""
            )
            if (
                len(body) >= FINAL_CLEANUP_RIGHT_SEQUENCE_WIDTH
                and body[-FINAL_CLEANUP_RIGHT_SEQUENCE_WIDTH:].strip().isdigit()
            ):
                body = body[:-FINAL_CLEANUP_RIGHT_SEQUENCE_WIDTH]
            return body.rstrip()

        return text.rstrip()

    def _logical(self, line: str) -> str:
        return self._body(line).strip()

    def _is_comment_or_debug(self, line: str) -> bool:
        text = str(line or "").rstrip("\n")
        if (
            len(text) >= FINAL_CLEANUP_INDICATOR_COLUMN
            and text[:FINAL_CLEANUP_SEQUENCE_WIDTH].strip().isdigit()
        ):
            return (
                text[FINAL_CLEANUP_SEQUENCE_WIDTH:FINAL_CLEANUP_INDICATOR_COLUMN]
                in FINAL_CLEANUP_COMMENT_INDICATORS
            )

        stripped = text.strip()
        return (
            any(stripped.startswith(c) for c in FINAL_CLEANUP_COMMENT_CHARS)
            or stripped.upper().startswith(FINAL_CLEANUP_DEBUG_PREFIX)
        )

    def _paragraph_ranges(self, lines: list[str]) -> list[tuple[int, int]]:
        output: list[tuple[int, int]] = []
        current_start = -1

        for index, line in enumerate(lines):
            if not PARAGRAPH_HEADER_PATTERN.match(self._logical(line)):
                continue
            if current_start >= 0:
                output.append((current_start, index))
            current_start = index

        if current_start >= 0:
            output.append((current_start, len(lines)))

        return output

    def _paragraph_end_index(self, lines: list[str], start: int) -> int:
        index = start + 1
        while index < len(lines):
            logical = self._logical(lines[index])
            if index > start + 1 and PARAGRAPH_HEADER_PATTERN.match(logical):
                return index
            index += 1
        return len(lines)