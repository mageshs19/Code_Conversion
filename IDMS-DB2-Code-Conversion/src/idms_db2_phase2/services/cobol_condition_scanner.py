# LOCATION: src/idms_db2_phase2/services/cobol_condition_scanner.py
# ACTION: CREATE NEW FILE
"""Finds where a COBOL conditional expression ends.

A hand-written IF frequently spans lines:

    IF (DA-CPTAFS OF DCL... < DA-ARCH-YMD
        AND DA-CPTAFS OF DCL... NOT = '00000000') OR
        (DA-CRFMAS OF DCL... < DA-ARCH-YMD AND
        DA-CPTAFS OF DCL... = '00000000')
        PERFORM ...

Any pass that extracts a block MUST NOT cut between the IF keyword and the
first statement, or the condition is orphaned and the program will not
compile. Read-only: this service rewrites nothing.
"""

from __future__ import annotations

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from patterns.structural_safety_patterns import IF_START_PATTERN
from rules.structural_safety_rules import (
    CONDITION_CONTINUATION_TOKENS,
    CONDITION_SCAN_LIMIT,
    CONDITION_TERMINATING_VERBS,
)

COMMENT_PREFIXES = ("*", "/")


class CobolConditionScanner:
    """Locates the last line of a conditional expression."""

    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.fixed_format = fixed_format or FixedFormatLineService()

    # ---------------------------------------------------------- public
    def is_condition_start(self, line: str) -> bool:
        return bool(IF_START_PATTERN.match(self._logical(line)))

    def condition_end_index(self, lines: list[str], if_index: int) -> int:
        """Index of the LAST line belonging to the IF condition.

        Returns if_index when the whole condition fits on the IF line.
        Returns -1 when the condition cannot be resolved, which callers
        must treat as "refuse to extract".

        CORRECTION - a dangling operator closed the condition
        -----------------------------------------------------
        The termination test inspected only the NEXT line's first word:

            if depth <= 0 and not self._continues_condition(body):
                return index - 1

        so this four-line condition was measured as ONE line:

            IF (HELP-DA-CPTAFS-479BFAS < DA-ARCH-YMD  AND
            HELP-DA-CPTAFS-479BFAS NOT = '00000000') OR

        Line 1 ends on AND; line 2 opens with a data-name, which is
        neither a continuation token nor "(", so the scan stopped.
        OutputWriteGuard then saw a single-line condition, allowed the
        extraction, and the IF was cut from its own condition tail.

        A line ending on AND / OR / NOT has no right operand yet. The
        condition CANNOT end there, whatever follows. This is the first
        of the three clauses in this module's own contract, and it was
        the one missing from the code.
        """
        if not 0 <= if_index < len(lines):
            return -1

        logical = self._logical(lines[if_index])
        if not IF_START_PATTERN.match(logical):
            return -1

        remainder = logical[2:].strip()
        if (
            self._holds_statement(remainder)
            and self._balanced(remainder)
            and not self._ends_on_boolean(remainder)
        ):
            return if_index

        depth = self._depth(remainder)
        previous = remainder
        end = min(len(lines), if_index + 1 + CONDITION_SCAN_LIMIT)

        for index in range(if_index + 1, end):
            body = self._logical(lines[index])

            if not body or self._is_comment(body):
                continue

            # The PREVIOUS line left an operator hanging, so this line is
            # its right operand and belongs to the condition. Absorb it
            # and test termination on the NEXT iteration.
            if self._ends_on_boolean(previous):
                depth += self._depth(body)
                previous = body
                continue

            depth += self._depth(body)

            if depth <= 0 and self._starts_statement(body):
                return index - 1

            if depth <= 0 and not self._continues_condition(body):
                return index - 1

            previous = body

        return -1

    @staticmethod
    def _ends_on_boolean(body: str) -> bool:
        """True when the line's last token is AND / OR / NOT.

        Such a line has an operator with no right operand, so the
        condition must continue onto the next line.
        """
        parts = str(body or "").strip().rstrip(".").split()
        return bool(parts) and parts[-1].upper() in CONDITION_CONTINUATION_TOKENS
    
    def spans_multiple_lines(self, lines: list[str], if_index: int) -> bool:
        end = self.condition_end_index(lines, if_index)
        return end < 0 or end > if_index

    def condition_line_count(self, lines: list[str], if_index: int) -> int:
        end = self.condition_end_index(lines, if_index)
        if end < 0:
            return CONDITION_SCAN_LIMIT
        return (end - if_index) + 1

    # -------------------------------------------------------- helpers
    def _logical(self, line: str) -> str:
        try:
            return str(self.fixed_format.logical(line) or "").strip()
        except Exception:  # noqa: BLE001
            return str(line or "").strip()

    @staticmethod
    def _is_comment(body: str) -> bool:
        return body.startswith(COMMENT_PREFIXES)

    @staticmethod
    def _depth(body: str) -> int:
        return body.count("(") - body.count(")")

    @staticmethod
    def _balanced(body: str) -> bool:
        return body.count("(") == body.count(")")

    @staticmethod
    def _first_word(body: str) -> str:
        parts = str(body or "").strip().split()
        return parts[0].upper() if parts else ""

    def _starts_statement(self, body: str) -> bool:
        return self._first_word(body) in CONDITION_TERMINATING_VERBS

    def _continues_condition(self, body: str) -> bool:
        word = self._first_word(body)
        if word in CONDITION_CONTINUATION_TOKENS:
            return True
        return body.startswith("(")

    def _holds_statement(self, remainder: str) -> bool:
        """True when the IF line already carries its first statement."""
        for verb in CONDITION_TERMINATING_VERBS:
            if f" {verb} " in f" {remainder.upper()} ":
                return True
        return False


__all__ = ["CobolConditionScanner"]