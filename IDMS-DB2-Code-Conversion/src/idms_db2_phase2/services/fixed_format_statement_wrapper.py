# LOCATION: src/idms_db2_phase2/services/fixed_format_statement_wrapper.py
# ACTION: CREATE NEW FILE

"""Wrap-aware fixed-format body replacement.

Any transformer that lengthens a statement in place must route through
this service. Replacing the body directly truncates at column 72, which
produces an undefined data name such as WS-NR-ID-GO.

Mirrors the proven splitter in SqlcodeWrapperLineUtils, but is reusable
from business-paragraph transformers rather than generated SQL blocks only.
"""

from __future__ import annotations

from patterns.fixed_format_wrap_patterns import MOVE_TO_PATTERN
from rules.fixed_format_wrap_rules import (
    BODY_WIDTH,
    CONTINUATION_INDENT,
    DIAG_WRAPPED_TEMPLATE,
    BODY_END_COLUMN,
    TOKEN_MOVE,
    TOKEN_OF_DCL,
    TOKEN_TO,
)


class FixedFormatStatementWrapper:

    def __init__(self, fixed_format) -> None:
        self.fixed_format = fixed_format
        self.messages: list[str] = []

    def replace_body(
        self,
        line: str,
        new_body: str,
    ) -> list[str]:
        """Replace a fixed-format body, wrapping when it no longer fits.

        Returns one or more physical lines. Callers must extend, not append.
        """
        body = str(new_body or "").rstrip()

        if not self.fixed_format.is_fixed_line(line):
            return [body]

        indent = self._leading_spaces(body)
        fragments = self._wrap(body=body, indent=indent)

        if len(fragments) > 1:
            self.messages.append(
                DIAG_WRAPPED_TEMPLATE.format(column=BODY_END_COLUMN)
            )

        return [
            self.fixed_format.replace_body(line, fragment)
            for fragment in fragments
        ]

    def _wrap(self, body: str, indent: str) -> list[str]:
        if len(body) <= BODY_WIDTH:
            return [body]

        move_lines = self._wrap_move(body=body, indent=indent)
        if move_lines:
            return move_lines

        return self._wrap_by_words(
            body=body,
            continuation_indent=indent + CONTINUATION_INDENT,
        )

    def _wrap_move(self, body: str, indent: str) -> list[str]:
        """Split MOVE <source> TO <target> on the TO boundary.

        A source qualified with OF DCL is always split, matching the
        generated-block convention, so the target can never be clipped.
        """
        match = MOVE_TO_PATTERN.match(body.strip())
        if not match:
            return []

        source = str(match.group("source") or "").strip()
        target = str(match.group("target") or "").strip()
        dot = str(match.group("dot") or "").strip()

        if not source or not target:
            return []

        one_line = f"{indent}{TOKEN_MOVE} {source} {TOKEN_TO} {target}{dot}"
        force_split = TOKEN_OF_DCL in source.upper()

        if len(one_line) <= BODY_WIDTH and not force_split:
            return [one_line]

        return [
            f"{indent}{TOKEN_MOVE} {source}",
            f"{indent}{TOKEN_TO} {target}{dot}",
        ]

    def _wrap_by_words(
        self,
        body: str,
        continuation_indent: str,
    ) -> list[str]:
        words = body.split()
        if not words:
            return [body]

        indent = self._leading_spaces(body)
        output: list[str] = []
        current = indent

        for word in words:
            candidate = f"{current}{word}" if not current.strip() else f"{current} {word}"
            if len(candidate) <= BODY_WIDTH:
                current = candidate
                continue

            output.append(current.rstrip())
            current = f"{continuation_indent}{word}"

        if current.strip():
            output.append(current.rstrip())

        return output or [body]

    @staticmethod
    def _leading_spaces(text: str) -> str:
        raw = str(text or "")
        return raw[: len(raw) - len(raw.lstrip())]