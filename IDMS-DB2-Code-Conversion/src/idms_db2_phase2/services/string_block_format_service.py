"""
STRING block format service.

Reformats COBOL STRING blocks into manual style after Area B alignment.
Extracted from the former final fix composer.
"""

from __future__ import annotations

from patterns.final_feedback_fix_patterns import (
    STRING_END_PATTERN,
    STRING_INTO_PATTERN,
    STRING_START_PATTERN,
)
from rules.final_feedback_fix_rules import (
    FINAL_FIX_STRING_CONTINUATION_BODY_INDENT,
    FINAL_FIX_STRING_INTO_BODY_INDENT,
    FINAL_FIX_STRING_START_BODY_INDENT,
)
from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)


class StringBlockFormatService:
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
        inside_string = False

        for line in lines:
            logical = self.fixed_format.logical(line)
            stripped = str(logical or "").strip()

            if not stripped:
                output.append(line)
                continue

            if self.fixed_format.is_comment_or_control_line(line):
                output.append(line)
                continue

            if STRING_START_PATTERN.match(stripped):
                inside_string = True
                output.append(
                    self._replace_body_when_fits(
                        line=line,
                        body=FINAL_FIX_STRING_START_BODY_INDENT + stripped,
                    )
                )
                continue

            if inside_string and STRING_END_PATTERN.match(stripped):
                inside_string = False
                output.append(
                    self._replace_body_when_fits(
                        line=line,
                        body=FINAL_FIX_STRING_START_BODY_INDENT + stripped,
                    )
                )
                continue

            if inside_string and STRING_INTO_PATTERN.match(stripped):
                output.append(
                    self._replace_body_when_fits(
                        line=line,
                        body=FINAL_FIX_STRING_INTO_BODY_INDENT + stripped,
                    )
                )
                continue

            if inside_string:
                output.append(
                    self._replace_body_when_fits(
                        line=line,
                        body=(
                            FINAL_FIX_STRING_CONTINUATION_BODY_INDENT
                            + stripped
                        ),
                    )
                )
                continue

            output.append(line)

        return "\n".join(output).rstrip() + "\n"

    def _replace_body_when_fits(self, line: str, body: str) -> str:
        clean_body = str(body or "").rstrip()

        if not self.fixed_format.is_fixed_line(line):
            return clean_body

        if len(clean_body) > self.fixed_format.BODY_WIDTH:
            return line

        return self.fixed_format.replace_body(line, clean_body)