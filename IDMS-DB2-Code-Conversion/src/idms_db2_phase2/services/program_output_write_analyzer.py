from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer
from idms_db2_phase2.services.program_flow_models import OutputWrite, ParagraphSpan
from idms_db2_phase2.services.program_paragraph_analyzer import (
    ProgramParagraphAnalyzer,
)
from rules.program_flow_rules import WRITE_TOKENS


class ProgramOutputWriteAnalyzer:
    """
    Detects basic output write statements for diagnostics.

    This class does not rewrite COBOL.
    """

    def __init__(
        self,
        paragraph_analyzer: ProgramParagraphAnalyzer | None = None,
    ) -> None:
        self.paragraph_analyzer = paragraph_analyzer or ProgramParagraphAnalyzer()

    def output_writes(
        self,
        logical_lines: list[tuple[int, str, str]],
        paragraphs: list[ParagraphSpan],
    ) -> list[OutputWrite]:
        output: list[OutputWrite] = []
        paragraph_by_line = self.paragraph_analyzer.paragraph_name_by_line(paragraphs)

        for line_number, logical, _raw_line in logical_lines:
            upper = logical.strip().upper()

            if not any(upper.startswith(token) for token in WRITE_TOKENS):
                continue

            output.append(
                OutputWrite(
                    output_record=self.first_word_after_operation(upper),
                    paragraph_name=paragraph_by_line.get(line_number, ""),
                    write_line=line_number,
                )
            )

        return output

    def first_word_after_operation(
        self,
        upper_line: str,
    ) -> str:
        parts = upper_line.split()

        if len(parts) < 2:
            return ""

        return NameNormalizer.normalize(parts[1].rstrip("."))