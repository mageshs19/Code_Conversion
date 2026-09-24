# LOCATION: src/idms_db2_phase2/composers/db2_date_field_detector.py
# ACTION: REPLACE ENTIRE FILE

"""Detects DB2 DATE hosts that take part in a COBOL comparison.

Detection logic only. Owns no regex (patterns live in
patterns/db2_date_patterns.py) and no templates.

CORRECTION - detection was single-line and name-bound
------------------------------------------------------
The old detector matched one physical line against a pattern that
required the DATE host to be the first token after IF AND required the
literal token PARMDATE somewhere in the condition. Any parenthesised,
compound, multi-line or differently-named comparison returned an empty
field list, so the composer's `if date_fields:` guard was False and the
whole pass was skipped without a word.

Detection now works on an ASSEMBLED condition and names no business
field: a DATE host is recognised by its DCLGEN-qualified shape, and it
counts only when the condition also carries a comparison operator.
"""

from __future__ import annotations

from dataclasses import dataclass

from idms_db2_phase2.composers.db2_date_condition_assembler import (
    ConditionSpan,
    Db2DateConditionAssembler,
)
from idms_db2_phase2.composers.db2_date_line_utils import Db2DateLineUtils
from patterns.db2_date_patterns import (
    COMPARISON_OPERATOR_PATTERN,
    DB2_DATE_HOST_OPERAND_PATTERN,
    DB2_SHARED_DATE_HELPER_USAGE_PATTERN,
    PROCEDURE_DIVISION_PATTERN,
    SQL_HOST_OPERAND_PATTERN,
)


@dataclass(frozen=True)
class DateOperand:
    """One `DA-xxx OF DCLyyy` reference inside a condition."""

    field: str = ""
    group: str = ""

    @property
    def reference(self) -> str:
        return f"{self.field} OF {self.group}"


class Db2DateFieldDetector:
    def __init__(
        self,
        line_utils: Db2DateLineUtils | None = None,
        assembler: Db2DateConditionAssembler | None = None,
    ) -> None:
        self.line_utils = line_utils or Db2DateLineUtils()
        self.assembler = assembler or Db2DateConditionAssembler(
            self.line_utils
        )

    #
    # Public entry points
    #
    def date_fields_used_in_comparisons(
        self,
        lines: list[str],
    ) -> list[str]:
        """Distinct DATE host field names compared anywhere, in order."""
        output: list[str] = []
        seen: set[str] = set()

        for span in self.assembler.spans(lines):
            for operand in self.operands_in(span):
                name = self.line_utils.clean_cobol_name(operand.field)

                if not name or name in seen:
                    continue

                seen.add(name)
                output.append(name)

        return output

    def operands_in(self, span: ConditionSpan) -> list[DateOperand]:
        """Every DATE operand of one condition, duplicates removed.

        Returns [] when the condition carries no comparison operator: a
        bare reference inside an IF is not a comparison and must not
        trigger a rewrite.
        """
        text = str(getattr(span, "text", "") or "")

        if not text:
            return []

        if not COMPARISON_OPERATOR_PATTERN.search(text):
            return []

        # An SQL host reference (:DCLGRP.FIELD) is never rewritten.
        scannable = SQL_HOST_OPERAND_PATTERN.sub(" ", text)

        output: list[DateOperand] = []
        seen: set[tuple[str, str]] = set()

        for found in DB2_DATE_HOST_OPERAND_PATTERN.finditer(scannable):
            field = self.line_utils.clean_cobol_name(found.group("field"))
            group = self.line_utils.clean_cobol_name(found.group("group"))

            if not field or not group:
                continue

            key = (field, group)

            if key in seen:
                continue

            seen.add(key)
            output.append(DateOperand(field=field, group=group))

        return output

    def shared_date_helpers_used_in_procedure(
        self,
        lines: list[str],
    ) -> bool:
        in_procedure_division = False

        for line in lines:
            logical = self.line_utils.logical(line)

            if not logical:
                continue

            if PROCEDURE_DIVISION_PATTERN.match(logical):
                in_procedure_division = True
                continue

            if not in_procedure_division:
                continue

            if self.line_utils.is_comment_or_blank(logical):
                continue

            if DB2_SHARED_DATE_HELPER_USAGE_PATTERN.search(logical):
                return True

        return False


__all__ = ["DateOperand", "Db2DateFieldDetector"]