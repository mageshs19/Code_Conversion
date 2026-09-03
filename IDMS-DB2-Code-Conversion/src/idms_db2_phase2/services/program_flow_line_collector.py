from __future__ import annotations

from patterns.sequence_patterns import strip_sequence_numbers


class ProgramFlowLineCollector:
    """
    Converts COBOL source text into line-numbered logical lines.

    Output tuple format:
    - line number
    - logical line without sequence area
    - original raw line with trailing newline removed
    """

    def logical_lines_with_numbers(
        self,
        cobol_text: str,
    ) -> list[tuple[int, str, str]]:
        output: list[tuple[int, str, str]] = []

        for line_number, raw_line in enumerate(
            str(cobol_text or "").splitlines(),
            start=1,
        ):
            logical = strip_sequence_numbers(raw_line)
            output.append((line_number, logical, raw_line.rstrip()))

        return output