"""
Cursor flow rewriter.

Rewrites the mechanical cursor execution flow into manual-style flow and
converts generated FETCH paragraphs so that WHEN ZERO / CONTINUE performs
the business paragraph. Rewriting logic only.
"""

from idms_db2_phase2.composers.cursor_flow_line_formatter import (
    CursorFlowLineFormatter,
)
from idms_db2_phase2.composers.cursor_flow_models import CursorFlowPlan
from patterns.cursor_flow_patterns import (
    ANY_PARAGRAPH_HEADER_PATTERN,
    CONTINUE_PATTERN,
    CURSOR_PARAGRAPH_HEADER_PATTERN,
    WHEN_ZERO_PATTERN,
)
from rules.cursor_flow_rules import (
    NON_PARAGRAPH_DOTTED_LINES,
    NON_PARAGRAPH_HEADER_PREFIXES,
)


class CursorFlowRewriter:
    def __init__(
        self,
        line_formatter: CursorFlowLineFormatter | None = None,
    ) -> None:
        self.line_formatter = line_formatter or CursorFlowLineFormatter()

    def _logical(self, line: str) -> str:
        return self.line_formatter.logical(line)

    def rewrite_main_flow(
        self,
        lines: list[str],
        plans: list[CursorFlowPlan],
    ) -> list[str]:
        plan_by_open_index = {plan.open_index: plan for plan in plans}

        indexes_to_skip: set[int] = set()
        for plan in plans:
            indexes_to_skip.add(plan.fetch_index)
            indexes_to_skip.add(plan.business_index)
            indexes_to_skip.add(plan.until_index)

        output: list[str] = []

        for index, line in enumerate(lines):
            if index in indexes_to_skip:
                continue

            plan = plan_by_open_index.get(index)
            if plan is None:
                output.append(line)
                continue

            output.append(line)
            output.append(
                self.line_formatter.format_like_line(
                    reference_line=line,
                    replacement_body=(
                        f"PERFORM {plan.fetch_paragraph} "
                        f"UNTIL {plan.eoc_condition}."
                    ),
                )
            )
            output.append(
                self.line_formatter.format_like_line(
                    reference_line=line,
                    replacement_body=f"PERFORM {plan.close_paragraph}.",
                )
            )

        return output

    def rewrite_fetch_paragraphs(
        self,
        lines: list[str],
        plans: list[CursorFlowPlan],
    ) -> list[str]:
        business_by_fetch_paragraph = {
            plan.fetch_paragraph.upper(): plan.business_paragraph
            for plan in plans
        }

        output: list[str] = []
        index = 0

        while index < len(lines):
            logical = self._logical(lines[index])
            header_match = CURSOR_PARAGRAPH_HEADER_PATTERN.match(logical)

            if not header_match:
                output.append(lines[index])
                index += 1
                continue

            if header_match.group("operation").upper() != "FETCH":
                output.append(lines[index])
                index += 1
                continue

            fetch_paragraph = (
                f"{header_match.group('number')}-"
                f"FETCH-"
                f"{header_match.group('cursor')}"
            ).upper()

            business_paragraph = business_by_fetch_paragraph.get(
                fetch_paragraph
            )
            if not business_paragraph:
                output.append(lines[index])
                index += 1
                continue

            paragraph_lines, next_index = self._collect_paragraph(
                lines=lines,
                start_index=index,
            )
            output.extend(
                self._replace_when_zero_continue(
                    paragraph_lines=paragraph_lines,
                    business_paragraph=business_paragraph,
                )
            )
            index = next_index

        return output

    def _collect_paragraph(
        self,
        lines: list[str],
        start_index: int,
    ) -> tuple[list[str], int]:
        output = [lines[start_index]]
        index = start_index + 1

        while index < len(lines):
            logical = self._logical(lines[index])

            if CURSOR_PARAGRAPH_HEADER_PATTERN.match(logical):
                break
            if self._is_non_cursor_paragraph_header(logical):
                break

            output.append(lines[index])
            index += 1

        return output, index

    def _replace_when_zero_continue(
        self,
        paragraph_lines: list[str],
        business_paragraph: str,
    ) -> list[str]:
        output: list[str] = []
        index = 0

        while index < len(paragraph_lines):
            line = paragraph_lines[index]
            logical = self._logical(line)
            output.append(line)

            if not WHEN_ZERO_PATTERN.match(logical):
                index += 1
                continue

            next_index = self._next_non_blank_index(
                lines=paragraph_lines,
                start_index=index + 1,
            )
            if next_index < 0:
                index += 1
                continue

            next_line = paragraph_lines[next_index]
            if not CONTINUE_PATTERN.match(self._logical(next_line)):
                index += 1
                continue

            output.extend(paragraph_lines[index + 1 : next_index])
            output.append(
                self.line_formatter.format_like_line(
                    reference_line=next_line,
                    replacement_body=f"PERFORM {business_paragraph}",
                )
            )
            index = next_index + 1

        return output

    def _next_non_blank_index(
        self,
        lines: list[str],
        start_index: int,
    ) -> int:
        for index in range(start_index, len(lines)):
            if self._logical(lines[index]):
                return index
        return -1

    def _is_non_cursor_paragraph_header(self, logical: str) -> bool:
        normalized = str(logical or "").strip().upper()

        if not normalized:
            return False
        if normalized in NON_PARAGRAPH_DOTTED_LINES:
            return False
        if normalized.startswith(NON_PARAGRAPH_HEADER_PREFIXES):
            return False
        if not ANY_PARAGRAPH_HEADER_PATTERN.match(normalized):
            return False
        if CURSOR_PARAGRAPH_HEADER_PATTERN.match(normalized):
            return False

        return True