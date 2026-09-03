from __future__ import annotations

from idms_db2_phase2.services.program_flow_models import ParagraphSpan
from patterns.cobol_patterns import PARAGRAPH_PATTERN, PROCEDURE_DIVISION_PATTERN


class ProgramParagraphAnalyzer:
    """
    Detects Procedure Division paragraph spans.

    This analyzer does not rewrite COBOL.
    """

    def paragraph_spans(
        self,
        logical_lines: list[tuple[int, str, str]],
    ) -> list[ParagraphSpan]:
        paragraphs: list[ParagraphSpan] = []
        current: ParagraphSpan | None = None
        inside_procedure = False

        for line_number, logical, raw_line in logical_lines:
            if PROCEDURE_DIVISION_PATTERN.match(logical):
                inside_procedure = True

            if not inside_procedure:
                continue

            match = PARAGRAPH_PATTERN.match(logical.strip())

            if match:
                if current is not None:
                    current.end_line = line_number - 1
                    paragraphs.append(current)

                current = ParagraphSpan(
                    name=match.group("name").upper(),
                    start_line=line_number,
                    end_line=line_number,
                    lines=[raw_line],
                )
                continue

            if current is not None:
                current.lines.append(raw_line)
                current.end_line = line_number

        if current is not None:
            paragraphs.append(current)

        return paragraphs

    def paragraph_name_by_line(
        self,
        paragraphs: list[ParagraphSpan],
    ) -> dict[int, str]:
        output: dict[int, str] = {}

        for paragraph in paragraphs:
            for line_number in range(paragraph.start_line, paragraph.end_line + 1):
                output[line_number] = paragraph.name

        return output