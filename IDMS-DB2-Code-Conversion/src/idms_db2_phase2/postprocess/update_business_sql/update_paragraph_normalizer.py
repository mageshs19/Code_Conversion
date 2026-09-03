from __future__ import annotations

from patterns.update_business_sql_patterns import (
    END_EVALUATE_PATTERN,
    END_EXEC_PATTERN,
    EVALUATE_SQLCODE_PATTERN,
    EXEC_SQL_START_PATTERN,
)
from rules.update_business_sql_rules import (
    NESTED_INDENT,
    SQL_BODY_INDENT,
    TOKEN_END_EVALUATE,
    TOKEN_END_EXEC,
    TOKEN_EVALUATE_SQLCODE,
    TOKEN_EXEC_SQL,
    TOKEN_WHEN,
    WHEN_INDENT,
)
from rules.update_restart_rules import UPDATE_SQL_PARAGRAPH_PREFIX


class UpdateParagraphNormalizer:
    """Normalizes generated update-paragraph indentation.

    Owns no column geometry; delegates line rendering to the host class
    (via _active_line_like / _logical / _is_comment_line).
    """

    def _normalize_all_update_paragraphs(self, lines: list[str]) -> list[str]:
        output = list(lines)
        index = 0

        while index < len(output):
            logical = self._logical(output[index]).upper().rstrip(".")

            if not logical.startswith(f"{UPDATE_SQL_PARAGRAPH_PREFIX}-"):
                index += 1
                continue

            paragraph_range = self.line_utils.find_paragraph_range(output, logical)
            if not paragraph_range:
                index += 1
                continue

            start, end = paragraph_range
            normalized = self._normalize_update_paragraph_lines(output[start:end])
            output = output[:start] + normalized + output[end:]
            index = start + len(normalized)

        return output

    def _normalize_update_paragraph_lines(
        self,
        paragraph_lines: list[str],
    ) -> list[str]:
        output: list[str] = []
        in_exec_sql = False
        in_evaluate = False

        for index, line in enumerate(paragraph_lines):
            logical = self._logical(line).strip()

            if index == 0 or not logical or self._is_comment_line(line):
                output.append(line)
                continue

            if EXEC_SQL_START_PATTERN.match(logical):
                in_exec_sql = True
                output.append(self._active_line_like(reference_line=line, body=TOKEN_EXEC_SQL))
                continue

            if in_exec_sql and END_EXEC_PATTERN.match(logical):
                in_exec_sql = False
                output.append(self._active_line_like(reference_line=line, body=TOKEN_END_EXEC))
                continue

            if in_exec_sql:
                output.append(
                    self._active_line_like(
                        reference_line=line,
                        body=f"{SQL_BODY_INDENT}{logical.rstrip('.')}",
                    )
                )
                continue

            if EVALUATE_SQLCODE_PATTERN.match(logical):
                in_evaluate = True
                output.append(
                    self._active_line_like(reference_line=line, body=TOKEN_EVALUATE_SQLCODE)
                )
                continue

            if in_evaluate and logical.upper().startswith(TOKEN_WHEN):
                output.append(
                    self._active_line_like(
                        reference_line=line,
                        body=f"{WHEN_INDENT}{logical.rstrip('.')}",
                    )
                )
                continue

            if in_evaluate and END_EVALUATE_PATTERN.match(logical):
                in_evaluate = False
                output.append(
                    self._active_line_like(reference_line=line, body=TOKEN_END_EVALUATE)
                )
                continue

            if in_evaluate:
                output.append(
                    self._active_line_like(
                        reference_line=line,
                        body=f"{NESTED_INDENT}{logical.rstrip('.')}",
                    )
                )
                continue

            output.append(self._active_line_like(reference_line=line, body=logical))

        return output