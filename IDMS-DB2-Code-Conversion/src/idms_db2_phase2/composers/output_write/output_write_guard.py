# LOCATION: src/idms_db2_phase2/composers/output_write/output_write_guard.py
# ACTION: CREATE NEW FILE
"""Structural safety gate for the output write extraction.

DEFECT THIS CLOSES
------------------
Extraction splices the call site in place of the IF BODY, cutting at
if_index + 1. That is correct only when the whole condition lives on the
IF line. A hand-written guard frequently spans lines:

    IF (DA-CPTAFS OF DCL... < DA-ARCH-YMD
        AND DA-CPTAFS OF DCL... NOT = '00000000') OR
        (DA-CRFMAS OF DCL... < DA-ARCH-YMD AND
        DA-CPTAFS OF DCL... = '00000000')
        PERFORM ...

Cutting at if_index + 1 leaves the IF with no condition tail and moves
the tail into the new paragraph, where it begins with a dangling AND.
The program does not compile.

The gate is deliberately PROGRAM-WIDE and coarse: when any PROCEDURE
DIVISION IF carries a multi-line condition, extraction is refused for
the whole program and a diagnostic is emitted. Refusing leaves working
COBOL; guessing produces source the compiler rejects.
"""

from __future__ import annotations

from idms_db2_phase2.composers.output_write.output_write_line_utils import (
    OutputWriteLineUtils,
)
from idms_db2_phase2.services.cobol_condition_scanner import (
    CobolConditionScanner,
)
from patterns.output_write_paragraph_patterns import (
    PROCEDURE_DIVISION_PATTERN,
)

SINGLE_LINE_CONDITION = 1


class OutputWriteGuard:
    """Refuses extraction when a guard condition spans lines."""

    def __init__(
        self,
        line_utils: OutputWriteLineUtils | None = None,
        condition_scanner: CobolConditionScanner | None = None,
    ) -> None:
        self.lines = line_utils or OutputWriteLineUtils()
        self.condition_scanner = condition_scanner or CobolConditionScanner(
            fixed_format=self.lines.fixed_format,
        )

    # ---------------------------------------------------------- public
    def blocks_extraction(self, text: str) -> bool:
        return self.widest_condition(text) > SINGLE_LINE_CONDITION

    def widest_condition(self, text: str) -> int:
        """Line count of the longest PROCEDURE DIVISION IF condition."""
        lines = (
            str(text or "")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .split("\n")
        )

        in_procedure = False
        widest = 0

        for index, line in enumerate(lines):
            logical = self.lines.logical(line)
            if not logical:
                continue

            if PROCEDURE_DIVISION_PATTERN.match(logical):
                in_procedure = True
                continue

            if not in_procedure:
                continue

            if self.lines.is_skippable(line):
                continue

            if not self.condition_scanner.is_condition_start(line):
                continue

            size = self.condition_scanner.condition_line_count(lines, index)
            widest = max(widest, size)

        return widest


__all__ = ["OutputWriteGuard"]