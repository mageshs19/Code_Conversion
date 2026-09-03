"""
COBOL Area A / Area B alignment service.

Generic behavior:
- Does not change 80-column sequencing.
- Does not change business logic.
- Only realigns Procedure Division executable statements to Area B when safe.
- Never truncates a fixed-format COBOL body to force alignment.
- Safely reflows long two-line Procedure Division statements by using the
  existing continuation line when available.

No program names, cursor names, DB2 tables, DB2 columns, DCLGEN groups,
or host variables are hardcoded.
"""

from __future__ import annotations

from patterns.final_feedback_fix_patterns import (
    END_EXEC_PATTERN,
    EXEC_SQL_START_PATTERN,
    PROCEDURE_DIVISION_TOKEN_PATTERN,
)
from rules.final_feedback_fix_rules import (
    AREA_B_BODY_INDENT,
    SQL_BODY_INDENT,
)
from idms_db2_phase2.services.cobol_area_alignment_classifier import (
    CobolAreaAlignmentClassifier,
)
from idms_db2_phase2.services.cobol_area_alignment_reflow import (
    CobolAreaAlignmentReflow,
)
from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)


class CobolAreaAlignmentService:
    """
    Aligns generated Procedure Division executable statements to Area B.

    Area B starts at physical column 12.
    Since COBOL body starts at physical column 8, four body spaces are used.

    Safety:
    - If adding the indent would exceed the fixed body width, the line is not
      blindly truncated.
    - If the next line is a continuation, this service combines both logical
      fragments and re-wraps them back into the same two physical lines.
    - If safe reflow is not possible, the original line is preserved.
    """

    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.fixed_format = fixed_format or FixedFormatLineService()
        self.classifier = CobolAreaAlignmentClassifier()
        self.reflow = CobolAreaAlignmentReflow(
            fixed_format=self.fixed_format,
            classifier=self.classifier,
        )

    def align(self, text: str) -> str:
        if not text:
            return ""

        lines = str(text).splitlines()
        output: list[str] = []

        in_procedure_division = False
        in_exec_sql = False
        index = 0

        while index < len(lines):
            line = lines[index]
            logical = self.fixed_format.logical(line)

            if PROCEDURE_DIVISION_TOKEN_PATTERN.search(logical):
                in_procedure_division = True
                output.append(line)
                index += 1
                continue

            if not in_procedure_division:
                output.append(line)
                index += 1
                continue

            if self.fixed_format.is_comment_or_control_line(line):
                output.append(line)
                index += 1
                continue

            if not logical:
                output.append(line)
                index += 1
                continue

            if EXEC_SQL_START_PATTERN.match(logical):
                in_exec_sql = True
                output.append(
                    self._replace_body_when_safe(
                        line=line,
                        new_body=SQL_BODY_INDENT + logical,
                    )
                )
                index += 1
                continue

            if in_exec_sql:
                output.append(
                    self._replace_body_when_safe(
                        line=line,
                        new_body=SQL_BODY_INDENT + logical,
                    )
                )

                if END_EXEC_PATTERN.search(logical):
                    in_exec_sql = False

                index += 1
                continue

            if self.classifier.is_area_a(logical):
                output.append(
                    self._replace_body_when_safe(
                        line=line,
                        new_body=logical,
                    )
                )
                index += 1
                continue

            aligned_body = AREA_B_BODY_INDENT + logical

            if self._body_fits(aligned_body):
                output.append(
                    self.fixed_format.replace_body(
                        line,
                        aligned_body,
                    )
                )
                index += 1
                continue

            reflowed_lines = self.reflow.try_reflow_with_next_line(
                current_line=line,
                next_line=lines[index + 1] if index + 1 < len(lines) else "",
                first_indent=AREA_B_BODY_INDENT,
            )

            if reflowed_lines:
                output.extend(reflowed_lines)
                index += 2
                continue

            output.append(line)
            index += 1

        return "\n".join(output)

    def _replace_body_when_safe(
        self,
        *,
        line: str,
        new_body: str,
    ) -> str:
        """
        Replace fixed-format body only when it will not truncate.

        This prevents corruption such as losing operators at the end of long
        Procedure Division statements.
        """

        if not self.fixed_format.is_fixed_line(line):
            return self.fixed_format.replace_body(line, new_body)

        if not self._body_fits(new_body):
            return line

        return self.fixed_format.replace_body(line, new_body)

    def _body_fits(
        self,
        body: str,
    ) -> bool:
        return len(str(body or "")) <= self.fixed_format.BODY_WIDTH