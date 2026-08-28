"""
DB2 date Working-Storage manager.

Ensures the shared DB2 date Working-Storage block and required HELP-* helper
fields exist, without duplicating WS-DATUMVELDEN or any HELP-* field.

Placement logic only. All templates come from
rules/db2_date_conversion_rules.py; all regex from patterns/db2_date_patterns.py.
"""

from idms_db2_phase2.composers.db2_date_line_utils import Db2DateLineUtils
from patterns.db2_date_patterns import (
    DATE_WORKING_STORAGE_MARKER_PATTERN,
    DB2_DATE_WORKING_STORAGE_BASE_PATTERN,
    LINKAGE_SECTION_PATTERN,
    PROCEDURE_DIVISION_PATTERN,
)
from rules.db2_date_conversion_rules import (
    DB2_DATE_BASE_WORKING_STORAGE_LINES,
    DB2_DATE_HELPER_FIELD_TEMPLATE,
)

WS_DATUMVELDEN_PREFIX = "01 WS-DATUMVELDEN"
LEVEL_01_PREFIX = "01 "


class Db2DateWorkingStorageManager:
    def __init__(
        self,
        line_utils: Db2DateLineUtils | None = None,
    ) -> None:
        self.line_utils = line_utils or Db2DateLineUtils()

    def _logical(self, line: str) -> str:
        return self.line_utils.logical(line)

    def ensure_date_working_storage(
        self,
        lines: list[str],
        date_fields: list[str],
    ) -> list[str]:
        """
        Ensure DB2 date Working-Storage exists.

        - If no date Working-Storage exists, insert the full base block.
        - If it already exists, add only missing HELP-* fields.
        - Update-only flows normally pass no date_fields, so only the base
          block is required.
        - Retrieval/date comparison flows may require HELP-* fields.
        """
        if not self._has_date_working_storage(lines):
            block = self._date_working_storage_block(date_fields)
            insert_index = self._date_working_storage_insert_index(lines)

            if insert_index < 0:
                return block + [""] + lines

            return lines[:insert_index] + block + [""] + lines[insert_index:]

        return self._ensure_missing_date_helper_fields(
            lines=lines,
            date_fields=date_fields,
        )

    def _ensure_missing_date_helper_fields(
        self,
        lines: list[str],
        date_fields: list[str],
    ) -> list[str]:
        """
        Add missing HELP-* date fields when WS-DATUMVELDEN already exists.

        This prevents a retrieval/date-comparison regression where the base
        date block exists but a newly required HELP-* field is missing.
        """
        if not date_fields:
            return lines

        missing_helpers: list[str] = []

        for field_name in date_fields:
            helper = self.line_utils.helper_name(field_name)

            if self._helper_declared(lines=lines, helper=helper):
                continue

            missing_helpers.append(helper)

        if not missing_helpers:
            return lines

        helper_lines = [
            DB2_DATE_HELPER_FIELD_TEMPLATE.format(helper=helper)
            for helper in missing_helpers
        ]

        insert_index = self._date_helper_insert_index(lines)

        if insert_index < 0:
            return lines + helper_lines

        return lines[:insert_index] + helper_lines + lines[insert_index:]

    def _helper_declared(
        self,
        lines: list[str],
        helper: str,
    ) -> bool:
        """
        Return True only when the HELP-* field is declared before PROCEDURE
        DIVISION. A PROCEDURE DIVISION usage must not count as a declaration,
        which avoids false positives on reruns.
        """
        helper_upper = str(helper or "").strip().upper()

        if not helper_upper:
            return True

        for line in lines:
            logical = self._logical(line)

            if PROCEDURE_DIVISION_PATTERN.match(logical):
                return False

            if helper_upper in logical.upper():
                return True

        return False

    def _date_helper_insert_index(self, lines: list[str]) -> int:
        """
        Return index where missing HELP-* fields should be inserted.

        Preferred placement:
        - Inside the existing date Working-Storage area.
        - Before LINKAGE SECTION.
        - Before PROCEDURE DIVISION when LINKAGE SECTION is absent.
        - Before the next 01-level item after WS-DATUMVELDEN.
        """
        ws_datumvelden_seen = False

        for index, line in enumerate(lines):
            logical = self._logical(line)
            upper_logical = logical.upper()

            if upper_logical.startswith(WS_DATUMVELDEN_PREFIX):
                ws_datumvelden_seen = True
                continue

            if not ws_datumvelden_seen:
                continue

            if LINKAGE_SECTION_PATTERN.match(logical):
                return index

            if PROCEDURE_DIVISION_PATTERN.match(logical):
                return index

            if upper_logical.startswith(LEVEL_01_PREFIX):
                return index

        return -1

    def _has_date_working_storage(self, lines: list[str]) -> bool:
        in_procedure_division = False

        for line in lines:
            logical = self._logical(line)

            if DATE_WORKING_STORAGE_MARKER_PATTERN.search(line):
                return True

            if PROCEDURE_DIVISION_PATTERN.match(logical):
                in_procedure_division = True

            if in_procedure_division:
                continue

            upper_logical = logical.upper()

            if upper_logical.startswith(WS_DATUMVELDEN_PREFIX):
                return True

            if DB2_DATE_WORKING_STORAGE_BASE_PATTERN.search(upper_logical):
                return True

        return False

    def _date_working_storage_insert_index(self, lines: list[str]) -> int:
        for index, line in enumerate(lines):
            logical = self._logical(line)

            if LINKAGE_SECTION_PATTERN.match(logical):
                return index

        for index, line in enumerate(lines):
            logical = self._logical(line)

            if PROCEDURE_DIVISION_PATTERN.match(logical):
                return index

        return -1

    def _date_working_storage_block(
        self,
        date_fields: list[str],
    ) -> list[str]:
        lines = list(DB2_DATE_BASE_WORKING_STORAGE_LINES)

        for field_name in date_fields:
            helper = self.line_utils.helper_name(field_name)

            lines.append(
                DB2_DATE_HELPER_FIELD_TEMPLATE.format(helper=helper)
            )

        return lines