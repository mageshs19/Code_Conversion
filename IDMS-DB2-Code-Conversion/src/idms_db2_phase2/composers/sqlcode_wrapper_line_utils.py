from __future__ import annotations

from patterns.sqlcode_wrapper_patterns import MOVE_TO_PATTERN
from patterns.sequence_patterns import strip_sequence_numbers
from rules.sqlcode_wrapper_rules import (
    BASE_INDENT,
    BODY_END_COLUMN,
    BODY_START_COLUMN,
    BODY_WIDTH,
    CONTINUATION_INDENT,
    DB2_COMMENT_PREFIX,
    FULL_LINE_WIDTH,
    INDICATOR_COLUMN,
    RIGHT_SEQUENCE_END,
    RIGHT_SEQUENCE_START,
    SEQUENCE_AREA_WIDTH,
    TOKEN_MOVE,
    TOKEN_OF_DCL,
    TOKEN_TO,
)


class SqlcodeWrapperLineUtils:
    """Line normalization, MOVE/word wrapping, and fixed-format helpers.

    Owns no marker/detection strings (rules) and no MOVE regex (patterns).
    """

    def _normalize_line_endings(self, text: str) -> str:
        return str(text or "").replace("\r\n", "\n").replace("\r", "\n")

    def _logical(self, line: str) -> str:
        return strip_sequence_numbers(str(line or "")).strip()

    def _wrap_logical_body(self, logical: str, indent: str) -> list[str]:
        text = str(logical or "").strip()
        if not text:
            return [indent.rstrip()]

        move_lines = self._wrap_move_statement(logical=text, indent=indent)
        if move_lines:
            return move_lines

        body = indent + text
        if len(body) <= BODY_WIDTH:
            return [body]

        return self._wrap_by_words(
            body=body,
            continuation_indent=indent + CONTINUATION_INDENT,
        )

    def _wrap_move_statement(self, logical: str, indent: str) -> list[str]:
        match = MOVE_TO_PATTERN.match(str(logical or "").strip())
        if not match:
            return []

        source = str(match.group("source") or "").strip()
        target = str(match.group("target") or "").strip()
        if not source or not target:
            return []

        force_split = TOKEN_OF_DCL in source.upper()
        one_line = f"{indent}{TOKEN_MOVE}{source} {TOKEN_TO}{target}"

        if len(one_line) <= BODY_WIDTH and not force_split:
            return [one_line]

        first_line = f"{indent}{TOKEN_MOVE}{source}"
        second_line = f"{indent}{TOKEN_TO}{target}"
        output: list[str] = []

        if len(first_line) <= BODY_WIDTH:
            output.append(first_line)
        else:
            output.extend(
                self._wrap_by_words(
                    body=first_line,
                    continuation_indent=indent + CONTINUATION_INDENT,
                )
            )

        if len(second_line) <= BODY_WIDTH:
            output.append(second_line)
        else:
            output.extend(
                self._wrap_by_words(
                    body=second_line,
                    continuation_indent=indent + CONTINUATION_INDENT,
                )
            )

        return output

    def _wrap_by_words(self, body: str, continuation_indent: str) -> list[str]:
        text = str(body or "").rstrip()
        if len(text) <= BODY_WIDTH:
            return [text]

        words = text.strip().split()
        output: list[str] = []
        current = ""

        for word in words:
            candidate = word if not current else current.rstrip() + " " + word
            if len(candidate) <= BODY_WIDTH:
                current = candidate
                continue
            if current:
                if output:
                    output.append(continuation_indent + current.strip())
                else:
                    output.append(current.strip())
            current = word

        if current:
            if output:
                output.append(continuation_indent + current.strip())
            else:
                output.append(current.strip())

        if not output:
            return [text[:BODY_WIDTH]]

        normalized: list[str] = []
        for index, line in enumerate(output):
            if index == 0:
                normalized.append(line[:BODY_WIDTH])
                continue
            if line.startswith(continuation_indent):
                normalized.append(line[:BODY_WIDTH])
            else:
                normalized.append(
                    (continuation_indent + line.strip())[:BODY_WIDTH]
                )

        return normalized

    def _replace_body_part(self, original_line: str, new_body: str) -> str:
        line = str(original_line or "").rstrip()

        if self._is_fixed_format_line(line):
            left = line[:SEQUENCE_AREA_WIDTH]
            indicator = line[INDICATOR_COLUMN]
            right = line[RIGHT_SEQUENCE_START:RIGHT_SEQUENCE_END]
            body = (
                str(new_body or "").rstrip()[:BODY_WIDTH].ljust(BODY_WIDTH)
            )
            return f"{left}{indicator}{body}{right}"

        return str(new_body or "").rstrip()

    def _format_comment_like_line(
        self, reference_line: str, comment_text: str
    ) -> str:
        line = str(reference_line or "").rstrip()
        clean_comment = str(comment_text or "").strip()

        if not clean_comment.upper().startswith(DB2_COMMENT_PREFIX):
            clean_comment = f"{DB2_COMMENT_PREFIX} {clean_comment}"

        body = f" {clean_comment}"

        if self._is_fixed_format_line(line):
            left = line[:SEQUENCE_AREA_WIDTH]
            right = line[RIGHT_SEQUENCE_START:RIGHT_SEQUENCE_END]
            body_area = body[:BODY_WIDTH].ljust(BODY_WIDTH)
            return f"{left}*{body_area}{right}"

        return f"*{body}"

    def _is_fixed_format_line(self, line: str) -> bool:
        text = str(line or "")
        if len(text) < FULL_LINE_WIDTH:
            return False
        if not text[:SEQUENCE_AREA_WIDTH].isdigit():
            return False
        if not text[RIGHT_SEQUENCE_START:RIGHT_SEQUENCE_END].isdigit():
            return False
        return True