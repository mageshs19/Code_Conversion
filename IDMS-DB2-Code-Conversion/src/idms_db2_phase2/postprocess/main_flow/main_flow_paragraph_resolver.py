from __future__ import annotations

from patterns.update_main_flow_patterns import (
    DIVISION_LINE_PATTERN,
    EXEC_SQL_LINE_PATTERN,
    MOVE_LINE_PATTERN,
    PARAGRAPH_HEADER_LINE_PATTERN,
    PERFORM_LINE_PATTERN,
    PERFORM_READ_FLAT_FILE_LINE_PATTERN,
    PERFORM_UNTIL_LINE_PATTERN,
    PROCEDURE_DIVISION_LINE_PATTERN,
    SECTION_LINE_PATTERN,
)
from rules.update_restart_rules import (
    MAIN_FLOW_READ_FLAT_FILE_PARAGRAPH,
    MAIN_FLOW_RESTART_PARAGRAPH_PREFIXES,
)


class MainFlowParagraphResolver:
    """Resolves and classifies the business processing paragraph."""

    def _resolve_process_paragraph_from_main_flow(
        self, *, lines, start_index, end_index
    ):
        for index in range(start_index, end_index):
            logical = self._logical(lines[index]).upper().rstrip(".")
            match = PERFORM_UNTIL_LINE_PATTERN.search(logical)
            if not match:
                continue

            paragraph = str(match.group("paragraph") or "").strip().upper()
            if not paragraph or paragraph == MAIN_FLOW_READ_FLAT_FILE_PARAGRAPH:
                continue
            if self._is_restart_or_utility_paragraph(paragraph):
                continue
            return paragraph

        return ""

    def _resolve_first_business_paragraph(self, *, lines):
        inside_procedure = False

        for index, line in enumerate(lines):
            logical = self._logical(line).strip()
            upper = logical.upper().rstrip(".")

            if PROCEDURE_DIVISION_LINE_PATTERN.match(logical):
                inside_procedure = True
                continue
            if not inside_procedure:
                continue
            if DIVISION_LINE_PATTERN.match(logical):
                break
            if not self._is_paragraph_header(logical):
                continue

            paragraph_name = upper
            if self._is_restart_or_utility_paragraph(paragraph_name):
                continue
            if self._paragraph_has_business_sql_or_moves(lines=lines, start_index=index):
                return paragraph_name

        return ""

    def _paragraph_has_business_sql_or_moves(self, *, lines, start_index):
        for index in range(start_index + 1, len(lines)):
            logical = self._logical(lines[index]).strip()
            upper = logical.upper()

            if index > start_index + 1 and self._is_paragraph_header(logical):
                return False
            if DIVISION_LINE_PATTERN.match(logical):
                return False
            if EXEC_SQL_LINE_PATTERN.search(upper):
                return True
            if MOVE_LINE_PATTERN.match(upper):
                return True
            if PERFORM_LINE_PATTERN.match(upper):
                return True

        return False

    def _paragraph_contains_perform_read_flat_file(self, paragraph_lines):
        for line in paragraph_lines:
            logical = self._logical(line).upper().rstrip(".")
            if PERFORM_READ_FLAT_FILE_LINE_PATTERN.match(logical):
                return True
        return False

    def _is_paragraph_header(self, logical):
        text = str(logical or "").strip()
        if not PARAGRAPH_HEADER_LINE_PATTERN.match(text):
            return False

        upper = text.upper().rstrip(".")
        if SECTION_LINE_PATTERN.match(text):
            return False
        if DIVISION_LINE_PATTERN.match(text):
            return False
        if self._is_restart_or_utility_paragraph(upper):
            return False
        return True

    def _is_restart_or_utility_paragraph(self, paragraph_name):
        name = str(paragraph_name or "").strip().upper().rstrip(".")
        if not name:
            return True
        if name == MAIN_FLOW_READ_FLAT_FILE_PARAGRAPH:
            return True
        return any(
            name.startswith(prefix)
            for prefix in MAIN_FLOW_RESTART_PARAGRAPH_PREFIXES
        )