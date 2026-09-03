"""
SQLCODE wrapper cleanup composer.

Removes contradictory SQLCODE wrappers left after redundant OBTAIN NEXT cursor
calls have been removed. Targets:

    IF NOT SQLCODE = 100
        * DB2: Removed redundant OBTAIN NEXT after cursor EOC loop.
        CONTINUE.
        IF SQLCODE = 100
            ...
        END-IF
    END-IF.

and rewrites it to a single cleanup comment plus the recovered inner body.

Detection strings and tokens live in rules/sqlcode_wrapper_rules.py; the MOVE
regex in patterns/sqlcode_wrapper_patterns.py; line/wrap helpers in
SqlcodeWrapperLineUtils.
"""

from __future__ import annotations

from idms_db2_phase2.composers.sqlcode_wrapper_line_utils import (
    SqlcodeWrapperLineUtils,
)
from rules.sqlcode_wrapper_rules import (
    BASE_INDENT,
    CHILD_INDENT,
    CLEANUP_COMMENT_TEXT,
    COMMENT_PREFIXES,
    INNER_IF_LOOKAHEAD,
    INNER_IF_TEXT,
    MARKER_LOOKAHEAD,
    OUTER_IF_TEXT,
    REMOVED_OBTAIN_NEXT_TEXT,
    TOKEN_END_IF,
    TOKEN_IF,
)


class SqlcodeWrapperCleanupComposer(SqlcodeWrapperLineUtils):
    def compose(self, text: str) -> str:
        if not text:
            return ""

        lines = self._normalize_line_endings(text).splitlines()
        output: list[str] = []
        index = 0

        while index < len(lines):
            logical = self._logical(lines[index]).upper()

            if OUTER_IF_TEXT not in logical:
                output.append(lines[index])
                index += 1
                continue

            block = self._try_extract_redundant_wrapper_block(
                lines=lines, start_index=index
            )
            if block is None:
                output.append(lines[index])
                index += 1
                continue

            replacement_lines, next_index = block
            output.extend(replacement_lines)
            index = next_index

        return "\n".join(output).rstrip() + "\n"

    def _try_extract_redundant_wrapper_block(
        self, lines: list[str], start_index: int
    ) -> tuple[list[str], int] | None:
        outer_line = lines[start_index]

        marker_index = self._find_marker_after_outer_if(
            lines=lines, start_index=start_index + 1
        )
        if marker_index < 0:
            return None

        inner_if_index = self._find_inner_if_sqlcode_100(
            lines=lines, start_index=marker_index + 1
        )
        if inner_if_index < 0:
            return None

        inner_end_index = self._find_matching_end_if(
            lines=lines, if_index=inner_if_index
        )
        if inner_end_index < 0:
            return None

        outer_end_index = self._find_matching_end_if(
            lines=lines, if_index=start_index
        )
        if outer_end_index < 0 or outer_end_index <= inner_end_index:
            return None

        inner_body = lines[inner_if_index + 1 : inner_end_index]
        normalized_inner_body = self._normalize_inner_body(lines=inner_body)

        replacement = [
            self._format_comment_like_line(
                reference_line=outer_line,
                comment_text=CLEANUP_COMMENT_TEXT,
            )
        ]
        replacement.extend(normalized_inner_body)

        return replacement, outer_end_index + 1

    def _find_marker_after_outer_if(
        self, lines: list[str], start_index: int
    ) -> int:
        end_index = min(len(lines), start_index + MARKER_LOOKAHEAD)
        for index in range(start_index, end_index):
            if REMOVED_OBTAIN_NEXT_TEXT in self._logical(lines[index]).upper():
                return index
        return -1

    def _find_inner_if_sqlcode_100(
        self, lines: list[str], start_index: int
    ) -> int:
        end_index = min(len(lines), start_index + INNER_IF_LOOKAHEAD)
        for index in range(start_index, end_index):
            if self._logical(lines[index]).upper().startswith(INNER_IF_TEXT):
                return index
        return -1

    def _find_matching_end_if(self, lines: list[str], if_index: int) -> int:
        depth = 0
        for index in range(if_index, len(lines)):
            logical = self._logical(lines[index]).upper().rstrip(".")
            if logical.startswith(TOKEN_IF):
                depth += 1
                continue
            if logical == TOKEN_END_IF:
                depth -= 1
                if depth == 0:
                    return index
        return -1

    def _normalize_inner_body(self, lines: list[str]) -> list[str]:
        output: list[str] = []
        first_content_seen = False

        for line in lines:
            logical = self._logical(line)

            if not logical:
                output.append(line)
                continue

            if any(logical.startswith(p) for p in COMMENT_PREFIXES):
                output.append(line)
                continue

            if not first_content_seen:
                output.extend(
                    self._normalized_lines_for_logical(
                        original_line=line, logical=logical, indent=BASE_INDENT
                    )
                )
                first_content_seen = True
                continue

            if logical.upper().rstrip(".") == TOKEN_END_IF:
                output.extend(
                    self._normalized_lines_for_logical(
                        original_line=line,
                        logical=TOKEN_END_IF,
                        indent=BASE_INDENT,
                    )
                )
                continue

            output.extend(
                self._normalized_lines_for_logical(
                    original_line=line, logical=logical, indent=CHILD_INDENT
                )
            )

        return output

    def _normalized_lines_for_logical(
        self, original_line: str, logical: str, indent: str
    ) -> list[str]:
        wrapped_bodies = self._wrap_logical_body(logical=logical, indent=indent)
        return [
            self._replace_body_part(original_line=original_line, new_body=body)
            for body in wrapped_bodies
        ]