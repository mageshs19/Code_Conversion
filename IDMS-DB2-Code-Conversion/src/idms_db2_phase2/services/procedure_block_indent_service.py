"""
Procedure block indent service.

Improves readability of Procedure Division blocks by indenting IF/ELSE/END-IF
and EVALUATE/WHEN/END-EVALUATE. Extracted from the former final fix composer.
"""

from __future__ import annotations

from patterns.final_feedback_fix_patterns import (
    DIVISION_PATTERN,
    ELSE_PATTERN,
    END_EVALUATE_PATTERN,
    END_IF_PATTERN,
    EVALUATE_START_PATTERN,
    EXEC_SQL_END_LINE_PATTERN,
    EXEC_SQL_START_PATTERN,
    IF_START_PATTERN,
    PARAGRAPH_PATTERN,
    PROCEDURE_DIVISION_PATTERN,
    SECTION_PATTERN,
    WHEN_PATTERN,
)
from rules.cobol_statement_rules import NON_PARAGRAPH_SINGLE_WORDS
from rules.final_feedback_fix_rules import (
    FINAL_FIX_AREA_B_INDENT,
    FINAL_FIX_NESTED_INDENT,
)
from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)


class ProcedureBlockIndentService:
    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.fixed_format = fixed_format or FixedFormatLineService()

    def apply(self, text: str) -> str:
        if not text:
            return ""

        lines = str(text or "").splitlines()
        output: list[str] = []

        in_procedure_division = False
        in_exec_sql = False
        block_depth = 0
        evaluate_stack: list[bool] = []

        for line in lines:
            logical = self.fixed_format.logical(line)
            stripped = str(logical or "").strip()
            upper = stripped.upper()

            if not stripped:
                output.append(line)
                continue

            if PROCEDURE_DIVISION_PATTERN.match(upper):
                in_procedure_division = True
                block_depth = 0
                evaluate_stack = []
                output.append(line)
                continue

            if not in_procedure_division:
                output.append(line)
                continue

            if DIVISION_PATTERN.match(upper) and not (
                PROCEDURE_DIVISION_PATTERN.match(upper)
            ):
                in_procedure_division = False
                block_depth = 0
                evaluate_stack = []
                output.append(line)
                continue

            if self.fixed_format.is_comment_or_control_line(line):
                output.append(line)
                continue

            if self._is_area_a_header(upper):
                output.append(line)
                continue

            if EXEC_SQL_START_PATTERN.match(upper):
                in_exec_sql = True
                output.append(
                    self._replace_body_when_fits(
                        line=line,
                        body=self._readable_body(
                            logical=stripped,
                            block_depth=self._effective_depth(
                                block_depth, evaluate_stack
                            ),
                        ),
                    )
                )
                continue

            if in_exec_sql:
                output.append(
                    self._replace_body_when_fits(
                        line=line,
                        body=self._readable_body(
                            logical=stripped,
                            block_depth=self._effective_depth(
                                block_depth, evaluate_stack
                            ),
                        ),
                    )
                )
                if EXEC_SQL_END_LINE_PATTERN.match(upper):
                    in_exec_sql = False
                continue

            if END_IF_PATTERN.match(upper):
                block_depth = max(0, block_depth - 1)
                output.append(
                    self._replace_body_when_fits(
                        line=line,
                        body=self._readable_body(
                            logical=stripped,
                            block_depth=self._effective_depth(
                                block_depth, evaluate_stack
                            ),
                        ),
                    )
                )
                continue

            if END_EVALUATE_PATTERN.match(upper):
                if evaluate_stack:
                    evaluate_stack.pop()
                block_depth = max(0, block_depth - 1)
                output.append(
                    self._replace_body_when_fits(
                        line=line,
                        body=self._readable_body(
                            logical=stripped,
                            block_depth=block_depth,
                        ),
                    )
                )
                continue

            if ELSE_PATTERN.match(upper):
                output.append(
                    self._replace_body_when_fits(
                        line=line,
                        body=self._readable_body(
                            logical=stripped,
                            block_depth=max(
                                0,
                                self._effective_depth(
                                    block_depth, evaluate_stack
                                )
                                - 1,
                            ),
                        ),
                    )
                )
                continue

            if WHEN_PATTERN.match(upper):
                if evaluate_stack:
                    evaluate_stack[-1] = True
                output.append(
                    self._replace_body_when_fits(
                        line=line,
                        body=self._readable_body(
                            logical=stripped,
                            block_depth=block_depth,
                        ),
                    )
                )
                continue

            output.append(
                self._replace_body_when_fits(
                    line=line,
                    body=self._readable_body(
                        logical=stripped,
                        block_depth=self._effective_depth(
                            block_depth, evaluate_stack
                        ),
                    ),
                )
            )

            if IF_START_PATTERN.match(upper):
                block_depth += 1
                continue

            if EVALUATE_START_PATTERN.match(upper):
                block_depth += 1
                evaluate_stack.append(False)
                continue

        return "\n".join(output).rstrip() + "\n"

    def _effective_depth(
        self,
        block_depth: int,
        evaluate_stack: list[bool],
    ) -> int:
        if evaluate_stack and evaluate_stack[-1]:
            return block_depth + 1
        return block_depth

    def _readable_body(
        self,
        logical: str,
        block_depth: int,
    ) -> str:
        clean_logical = str(logical or "").strip()
        depth = max(0, block_depth)
        return (
            FINAL_FIX_AREA_B_INDENT
            + (FINAL_FIX_NESTED_INDENT * depth)
            + clean_logical
        )

    def _is_area_a_header(self, logical: str) -> bool:
        upper = str(logical or "").strip().upper()

        if not upper:
            return False

        if SECTION_PATTERN.match(upper):
            return True

        if PARAGRAPH_PATTERN.match(upper):
            word = upper.rstrip(".")
            return word not in NON_PARAGRAPH_SINGLE_WORDS

        return False

    def _replace_body_when_fits(self, line: str, body: str) -> str:
        clean_body = str(body or "").rstrip()

        if not self.fixed_format.is_fixed_line(line):
            return clean_body

        if len(clean_body) > self.fixed_format.BODY_WIDTH:
            return line

        return self.fixed_format.replace_body(line, clean_body)