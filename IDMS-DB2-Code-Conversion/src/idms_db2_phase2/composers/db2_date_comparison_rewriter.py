# LOCATION: src/idms_db2_phase2/composers/db2_date_comparison_rewriter.py
# ACTION: REPLACE ENTIRE FILE

"""DB2 date comparison rewriter.

Emits a realignment block for every DB2 DATE host that takes part in a
COBOL comparison, then substitutes that host with its HELP- helper inside
the condition.

    IF (DA-CPTAFS-479BFAS OF DCLDZBFASTV < DA-ARCH-YMD
       AND DA-CPTAFS-479BFAS OF DCLDZBFASTV NOT = '00000000') OR ...

becomes

    * DB2: realigned 2 DB2 DATE host(s) before comparison.
    MOVE ZEROES TO DA-CCYYMMDD
    MOVE ZEROES TO HELP-DA-CPTAFS-479BFAS
    MOVE DA-CPTAFS-479BFAS OF DCLDZBFASTV TO DA-DD-MM-CCYY
    EVALUATE TRUE
      ...
    END-EVALUATE
    MOVE DA-CCYYMMDD-R TO HELP-DA-CPTAFS-479BFAS
    ... (same block per host) ...
    IF (HELP-DA-CPTAFS-479BFAS < DA-ARCH-YMD
       AND HELP-DA-CPTAFS-479BFAS NOT = '00000000') OR ...

FIXED-FORMAT GEOMETRY
---------------------
A COBOL record is four fixed column ranges:

    1-6     left sequence
    7       indicator
    8-72    body            <- the ONLY part this pass may touch
    73-80   right sequence

Substitution happens inside the body, the body is re-padded to 65
columns, and the record is reassembled. The author's line breaks and
indentation survive exactly.

CORRECTION 1 - substitution on the raw line moved the sequence area
--------------------------------------------------------------------
The first version ran the regex over the whole 80-column record.
`DA-CPTAFS-479BFAS OF DCLDZBFASTV` is 32 characters and
`HELP-DA-CPTAFS-479BFAS` is 22, so the line shrank by 10 and the right
sequence slid from column 73 to column 63. ProcedureIndentNormalizer
then read a body with sequence digits in it and wrapped it onto two
lines.

CORRECTION 2 - the FixedFormatLineService fallback returned the raw line
-------------------------------------------------------------------------
The second version called fixed_format.body(), guarded by

    except Exception: return str(line).rstrip()

The guard fired and returned the ENTIRE record as if it were the body.
That body did not fit 65 columns, replace_body_wrapped() wrapped it, and
the right-sequence digits were split off as a trailing token, producing

    002610        AND 0
    002620        HELP-DA-CPTAFS-479BFAS NOT = '00000000') OR 0

Column arithmetic is now done here, directly, with no fallback that can
return something other than a body. A substitution that cannot be
represented in 65 columns leaves the line UNCHANGED: a cosmetic pass
must never corrupt source.

Rewriting logic only. Templates live in rules/db2_date_conversion_rules.py;
regex lives in patterns/db2_date_patterns.py.
"""

from __future__ import annotations

import re

from idms_db2_phase2.composers.db2_date_condition_assembler import (
    Db2DateConditionAssembler,
)
from idms_db2_phase2.composers.db2_date_field_detector import (
    Db2DateFieldDetector,
)
from idms_db2_phase2.composers.db2_date_line_utils import Db2DateLineUtils
from rules.db2_date_conversion_rules import (
    CONDITION_SCAN_LIMIT,
    DB2_DATE_CONVERSION_BANNER_TEMPLATE,
    DB2_DATE_CONVERSION_LINE_TEMPLATES,
    DB2_DATE_HIGH_NUMERIC_LITERAL,
    DB2_DATE_HIGH_VALUE_LITERAL,
    DB2_DATE_LOW_VALUE_LITERAL,
    DB2_DATE_MESSAGES,
    DB2_DATE_REFUSAL_COMMENT_TEMPLATE,
    EMIT_DATE_REFUSAL_COMMENT,
    ENFORCE_DATE_COMPARISON_CONVERSION,
    MAX_DATE_OPERANDS_PER_CONDITION,
)

DEFAULT_INDENT = "    "

# Fixed-format column geometry, zero based, end exclusive.
LEFT_SEQUENCE_END = 6
INDICATOR_INDEX = 6
BODY_START = 7
BODY_END = 72
LINE_WIDTH = 80
BODY_WIDTH = BODY_END - BODY_START  # 65


class Db2DateComparisonRewriter:
    def __init__(
        self,
        line_utils: Db2DateLineUtils | None = None,
        assembler: Db2DateConditionAssembler | None = None,
        detector: Db2DateFieldDetector | None = None,
    ) -> None:
        self.line_utils = line_utils or Db2DateLineUtils()
        self.assembler = assembler or Db2DateConditionAssembler(
            self.line_utils
        )
        self.detector = detector or Db2DateFieldDetector(
            line_utils=self.line_utils,
            assembler=self.assembler,
        )
        self.messages: list[str] = []

    #
    # Public entry point
    #
    def rewrite_date_comparisons(self, lines: list[str]) -> list[str]:
        self.messages = []

        if not ENFORCE_DATE_COMPARISON_CONVERSION:
            return list(lines)

        output: list[str] = []
        index = 0
        converted_conditions = 0
        converted_hosts = 0

        while index < len(lines):
            span = self.assembler.span_at(lines, index)

            if span is None:
                output.append(lines[index])
                index += 1
                continue

            operands = self.detector.operands_in(span)

            if not operands:
                output.extend(lines[i] for i in span.line_indexes)
                index = span.end_index + 1
                continue

            refusal = self._refusal_reason(span, operands)

            if refusal:
                output.extend(self._refuse(span, operands, refusal))
                output.extend(lines[i] for i in span.line_indexes)
                index = span.end_index + 1
                continue

            indent = span.indent or DEFAULT_INDENT

            output.append(
                DB2_DATE_CONVERSION_BANNER_TEMPLATE.format(
                    indent=indent,
                    count=len(operands),
                )
            )

            for operand in operands:
                output.extend(self._conversion_block(indent, operand))

            output.extend(
                self._rewritten_condition_lines(lines, span, operands)
            )

            converted_conditions += 1
            converted_hosts += len(operands)
            index = span.end_index + 1

        if converted_conditions:
            self.messages.append(
                DB2_DATE_MESSAGES["converted"].format(
                    count=converted_hosts,
                    conditions=converted_conditions,
                )
            )

        return output

    #
    # Realignment block
    #
    def _conversion_block(self, indent: str, operand) -> list[str]:
        helper = self.line_utils.helper_name(operand.field)

        return [
            template.format(
                indent=indent,
                helper=helper,
                field_name=operand.field,
                group_name=operand.group,
                low_value=DB2_DATE_LOW_VALUE_LITERAL,
                high_value=DB2_DATE_HIGH_VALUE_LITERAL,
                high_numeric=DB2_DATE_HIGH_NUMERIC_LITERAL,
            )
            for template in DB2_DATE_CONVERSION_LINE_TEMPLATES
        ]

    #
    # Condition substitution
    #
    def _rewritten_condition_lines(
        self,
        lines: list[str],
        span,
        operands,
    ) -> list[str]:
        """Each physical line with `FIELD OF GROUP` replaced by its helper."""
        replacements = [
            (
                self._operand_pattern(operand),
                self.line_utils.helper_name(operand.field),
            )
            for operand in operands
        ]

        return [
            self._substitute(lines[position], replacements)
            for position in span.line_indexes
        ]

    def _substitute(self, line: str, replacements) -> str:
        """Rewrite columns 8-72 only, then reassemble the record.

        Total function. Returns the ORIGINAL line whenever the rewrite
        cannot be represented, so this pass can never corrupt source.
        """
        original = str(line or "").rstrip("\n")

        if not self._is_fixed_record(original):
            return self._apply(original, replacements)

        padded = original.ljust(LINE_WIDTH)

        left = padded[0:LEFT_SEQUENCE_END]
        indicator = padded[INDICATOR_INDEX:BODY_START]
        body = padded[BODY_START:BODY_END]
        right = padded[BODY_END:LINE_WIDTH]

        new_body = self._apply(body, replacements)

        if new_body == body:
            return original

        trimmed = new_body.rstrip()

        if len(trimmed) > BODY_WIDTH:
            # Not representable in 65 columns. Leave the line alone.
            return original

        return f"{left}{indicator}{trimmed.ljust(BODY_WIDTH)}{right}"

    @staticmethod
    def _is_fixed_record(line: str) -> bool:
        """Columns 1-6 numeric is the only reliable fixed-format marker."""
        text = str(line or "")

        if len(text) < BODY_START:
            return False

        return text[0:LEFT_SEQUENCE_END].isdigit()

    @staticmethod
    def _apply(text: str, replacements) -> str:
        output = str(text or "")

        for pattern, helper in replacements:
            output = pattern.sub(helper, output)

        return output

    @staticmethod
    def _operand_pattern(operand):
        """`FIELD OF GROUP` with flexible whitespace, whole-token only."""
        return re.compile(
            r"\b"
            + re.escape(operand.field)
            + r"\s+OF\s+"
            + re.escape(operand.group)
            + r"\b",
            flags=re.IGNORECASE,
        )

    #
    # Refusal
    #
    def _refusal_reason(self, span, operands) -> str:
        if not span.complete:
            self.messages.append(
                DB2_DATE_MESSAGES["condition_unterminated"].format(
                    line=span.start_index + 1,
                    limit=CONDITION_SCAN_LIMIT,
                )
            )
            return "the condition was not closed within the scan limit"

        if len(operands) > MAX_DATE_OPERANDS_PER_CONDITION:
            self.messages.append(
                DB2_DATE_MESSAGES["too_many_operands"].format(
                    line=span.start_index + 1,
                    count=len(operands),
                    limit=MAX_DATE_OPERANDS_PER_CONDITION,
                )
            )
            return "the condition carries too many DATE operands"

        return ""

    @staticmethod
    def _refuse(span, operands, reason: str) -> list[str]:
        """A pass that cannot convert must say so IN the generated COBOL."""
        if not EMIT_DATE_REFUSAL_COMMENT:
            return []

        indent = span.indent or DEFAULT_INDENT

        return [
            DB2_DATE_REFUSAL_COMMENT_TEMPLATE.format(
                indent=indent,
                field=operand.field,
                reason=f"{reason}; convert this comparison manually.",
            )
            for operand in operands
        ]


__all__ = ["Db2DateComparisonRewriter"]