"""
Cursor flow plan discoverer.

Scans generated COBOL lines and correlates each cursor OPEN with its
matching FETCH paragraph and business processing loop, producing a list
of CursorFlowPlan objects. Discovery logic only.
"""

from idms_db2_phase2.composers.cursor_flow_line_formatter import (
    CursorFlowLineFormatter,
)
from idms_db2_phase2.composers.cursor_flow_models import CursorFlowPlan
from patterns.cursor_flow_patterns import (
    PERFORM_BUSINESS_PATTERN,
    PERFORM_CURSOR_PATTERN,
    UNTIL_SQLCODE_100_PATTERN,
)
from rules.cursor_flow_rules import (
    LOOKAHEAD_LIMIT,
    UNTIL_LOOKAHEAD_LIMIT,
)


class CursorFlowPlanDiscoverer:
    def __init__(
        self,
        line_formatter: CursorFlowLineFormatter | None = None,
    ) -> None:
        self.line_formatter = line_formatter or CursorFlowLineFormatter()

    def _logical(self, line: str) -> str:
        return self.line_formatter.logical(line)

    def discover(self, lines: list[str]) -> list[CursorFlowPlan]:
        plans: list[CursorFlowPlan] = []
        index = 0

        while index < len(lines):
            logical = self._logical(lines[index])
            open_match = PERFORM_CURSOR_PATTERN.match(logical)

            if not open_match:
                index += 1
                continue

            if open_match.group("operation").upper() != "OPEN":
                index += 1
                continue

            plan = self._build_plan(
                lines=lines,
                open_index=index,
                open_match=open_match,
            )

            if plan is None:
                index += 1
                continue

            plans.append(plan)
            index = plan.until_index + 1

        return plans

    def _build_plan(
        self,
        lines: list[str],
        open_index: int,
        open_match,
    ) -> CursorFlowPlan | None:
        cursor_name = open_match.group("cursor").upper()
        open_number = int(open_match.group("number"))
        fetch_number = open_number + 10
        close_number = open_number + 20

        fetch_index = self._find_fetch_after_open(
            lines=lines,
            start_index=open_index + 1,
            cursor_name=cursor_name,
            fetch_number=fetch_number,
        )
        if fetch_index < 0:
            return None

        business_info = self._find_business_loop_after_fetch(
            lines=lines,
            start_index=fetch_index + 1,
        )
        if business_info is None:
            return None

        business_index, until_index, business_paragraph = business_info

        return CursorFlowPlan(
            cursor_name=cursor_name,
            open_number=open_number,
            fetch_number=fetch_number,
            close_number=close_number,
            open_paragraph=f"{open_number:03d}-OPEN-{cursor_name}",
            fetch_paragraph=f"{fetch_number:03d}-FETCH-{cursor_name}",
            close_paragraph=f"{close_number:03d}-CLOSE-{cursor_name}",
            eoc_condition=f"{cursor_name}-EOC",
            business_paragraph=business_paragraph,
            open_index=open_index,
            fetch_index=fetch_index,
            business_index=business_index,
            until_index=until_index,
        )

    def _find_fetch_after_open(
        self,
        lines: list[str],
        start_index: int,
        cursor_name: str,
        fetch_number: int,
    ) -> int:
        end_index = min(len(lines), start_index + LOOKAHEAD_LIMIT)

        for index in range(start_index, end_index):
            logical = self._logical(lines[index])
            match = PERFORM_CURSOR_PATTERN.match(logical)

            if not match:
                continue
            if match.group("operation").upper() != "FETCH":
                continue
            if match.group("cursor").upper() != cursor_name:
                continue
            if int(match.group("number")) != fetch_number:
                continue

            return index

        return -1

    def _find_business_loop_after_fetch(
        self,
        lines: list[str],
        start_index: int,
    ) -> tuple[int, int, str] | None:
        end_index = min(len(lines), start_index + LOOKAHEAD_LIMIT)

        for index in range(start_index, end_index):
            logical = self._logical(lines[index])

            if not logical:
                continue
            if logical.startswith("*") or logical.startswith("/"):
                continue
            if PERFORM_CURSOR_PATTERN.match(logical):
                continue

            business_match = PERFORM_BUSINESS_PATTERN.match(logical)
            if not business_match:
                continue

            business_paragraph = business_match.group("paragraph").upper()
            until_index = self._find_until_sqlcode_100(
                lines=lines,
                start_index=index + 1,
            )
            if until_index < 0:
                continue

            return index, until_index, business_paragraph

        return None

    def _find_until_sqlcode_100(
        self,
        lines: list[str],
        start_index: int,
    ) -> int:
        end_index = min(len(lines), start_index + UNTIL_LOOKAHEAD_LIMIT)

        for index in range(start_index, end_index):
            logical = self._logical(lines[index])
            if UNTIL_SQLCODE_100_PATTERN.match(logical):
                return index

        return -1