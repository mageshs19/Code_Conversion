from __future__ import annotations

from patterns.update_final_cleanup_patterns import (
    END_EVALUATE_PATTERN,
    END_EXEC_PATTERN,
    EVALUATE_SQLCODE_PATTERN,
    EXEC_SQL_PATTERN,
    PARAGRAPH_HEADER_PATTERN,
    PERFORM_PATTERN,
    PROCESS_COMMIT_IF_PATTERN,
    STOP_RUN_PATTERN,
    UPDATE_PARAGRAPH_PATTERN,
    WHEN_PATTERN,
)
from rules.update_cobol_final_cleanup_rules import (
    FINAL_CLEANUP_ACTION_INDENT,
    FINAL_CLEANUP_AREA_B,
    FINAL_CLEANUP_DOT,
    FINAL_CLEANUP_SQL_BODY,
    FINAL_CLEANUP_TOKEN_END_EVALUATE,
    FINAL_CLEANUP_TOKEN_END_EXEC,
    FINAL_CLEANUP_TOKEN_END_IF,
    FINAL_CLEANUP_TOKEN_END_IF_DOT,
    FINAL_CLEANUP_TOKEN_EVALUATE_SQLCODE,
    FINAL_CLEANUP_TOKEN_EXEC_SQL,
    FINAL_CLEANUP_TOKEN_PROCEDURE_DIVISION,
    FINAL_CLEANUP_TOKEN_STOP_RUN,
    FINAL_CLEANUP_WHEN_INDENT,
)


class FinalCleanupNormalizer:
    """Normalizes 1100-UPDATE-* paragraphs and PROCEDURE simple blocks."""

    def _normalize_update_paragraphs(self, lines: list[str]) -> list[str]:
        output = list(lines)
        index = 0
        while index < len(output):
            if not UPDATE_PARAGRAPH_PATTERN.match(self._logical(output[index])):
                index += 1
                continue
            end = self._paragraph_end_index(output, index)
            normalized = self._normalize_update_paragraph(output[index:end])
            output = output[:index] + normalized + output[end:]
            index += len(normalized)
        return output

    def _normalize_update_paragraph(self, lines: list[str]) -> list[str]:
        output: list[str] = []
        in_exec_sql = False
        in_evaluate = False

        for index, line in enumerate(lines):
            logical = self._logical(line)

            if index == 0 or not logical or self._is_comment_or_debug(line):
                output.append(line)
                continue

            if EXEC_SQL_PATTERN.match(logical):
                in_exec_sql = True
                output.append(
                    self._replace_body(line, FINAL_CLEANUP_AREA_B + FINAL_CLEANUP_TOKEN_EXEC_SQL)
                )
                continue

            if in_exec_sql and END_EXEC_PATTERN.match(logical):
                in_exec_sql = False
                output.append(
                    self._replace_body(line, FINAL_CLEANUP_AREA_B + FINAL_CLEANUP_TOKEN_END_EXEC)
                )
                continue

            if in_exec_sql:
                output.append(
                    self._replace_body(line, FINAL_CLEANUP_SQL_BODY + logical.rstrip("."))
                )
                continue

            if EVALUATE_SQLCODE_PATTERN.match(logical):
                in_evaluate = True
                output.append(
                    self._replace_body(
                        line, FINAL_CLEANUP_AREA_B + FINAL_CLEANUP_TOKEN_EVALUATE_SQLCODE
                    )
                )
                continue

            if in_evaluate and WHEN_PATTERN.match(logical):
                output.append(
                    self._replace_body(line, FINAL_CLEANUP_WHEN_INDENT + logical.rstrip("."))
                )
                continue

            if in_evaluate and END_EVALUATE_PATTERN.match(logical):
                in_evaluate = False
                output.append(
                    self._replace_body(
                        line, FINAL_CLEANUP_AREA_B + FINAL_CLEANUP_TOKEN_END_EVALUATE
                    )
                )
                continue

            if in_evaluate:
                output.append(
                    self._replace_body(line, FINAL_CLEANUP_ACTION_INDENT + logical.rstrip("."))
                )
                continue

            if logical == FINAL_CLEANUP_DOT:
                output.append(self._replace_body(line, FINAL_CLEANUP_AREA_B + "."))
                continue

            output.append(
                self._replace_body(line, FINAL_CLEANUP_AREA_B + logical.rstrip("."))
            )

        return output

    def _normalize_procedure_simple_blocks(self, lines: list[str]) -> list[str]:
        output: list[str] = []
        in_procedure = False
        inside_simple_if = False

        for line in lines:
            logical = self._logical(line)
            upper = logical.upper().rstrip(".")

            if upper.startswith(FINAL_CLEANUP_TOKEN_PROCEDURE_DIVISION):
                in_procedure = True
                output.append(line)
                continue

            if not in_procedure or self._is_comment_or_debug(line):
                output.append(line)
                continue

            if PARAGRAPH_HEADER_PATTERN.match(logical):
                inside_simple_if = False
                output.append(line)
                continue

            if STOP_RUN_PATTERN.match(logical):
                output.append(
                    self._replace_body(line, FINAL_CLEANUP_AREA_B + FINAL_CLEANUP_TOKEN_STOP_RUN)
                )
                continue

            if PROCESS_COMMIT_IF_PATTERN.match(logical):
                inside_simple_if = True
                output.append(
                    self._replace_body(line, FINAL_CLEANUP_AREA_B + logical.rstrip("."))
                )
                continue

            if inside_simple_if and PERFORM_PATTERN.match(logical):
                output.append(
                    self._replace_body(line, FINAL_CLEANUP_WHEN_INDENT + logical.rstrip("."))
                )
                continue

            if inside_simple_if and upper.startswith(FINAL_CLEANUP_TOKEN_END_IF):
                inside_simple_if = False
                output.append(
                    self._replace_body(line, FINAL_CLEANUP_AREA_B + FINAL_CLEANUP_TOKEN_END_IF_DOT)
                )
                continue

            output.append(line)

        return output