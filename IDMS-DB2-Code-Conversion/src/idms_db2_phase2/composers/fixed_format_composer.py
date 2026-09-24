"""
Fixed-format COBOL composer.

Orchestrates final physical COBOL formatting. Detailed responsibilities are
split into:
- fixed_format_line_parser.py
- fixed_format_body_formatter.py
- fixed_format_wrapper.py
- fixed_format_sequence_manager.py
- fixed_format_line_composer.py (per-line composition mixin)
- patterns/fixed_format_patterns.py
- rules/fixed_format_rules.py

Final physical layout:
- Columns 1-6   : left sequence number
- Column 7      : indicator area
- Columns 8-72  : COBOL body
- Columns 73-80 : right sequence number
"""

from idms_db2_phase2.composers.fixed_format_body_formatter import (
    FixedFormatBodyFormatter,
)
from idms_db2_phase2.composers.fixed_format_line_composer import (
    FixedFormatLineComposer,
)
from idms_db2_phase2.composers.fixed_format_line_parser import (
    FixedFormatLineParser,
)
from idms_db2_phase2.composers.fixed_format_sequence_manager import (
    FixedFormatSequenceManager,
)
from idms_db2_phase2.composers.fixed_format_wrapper import FixedFormatWrapper

from rules.fixed_format_rules import (
    BODY_WIDTH,
    FIXED_FORMAT_MESSAGES,
    TOTAL_WIDTH,
    VALID_INDICATORS,
)


class FixedFormatComposer(FixedFormatLineComposer):
    """Final fixed-format COBOL composer.

    Owns no regex patterns, layout constants, or sequence detection rules.
    It coordinates the helper classes; per-line composition is provided by
    FixedFormatLineComposer.

    Sequence numbering is generic:
    - Existing valid left sequence pattern is detected.
    - Existing valid manual-style right sequence pattern is detected.
    - Invalid small right sequence patterns are normalized by the manager.
    """

    def __init__(self) -> None:
        self.line_parser = FixedFormatLineParser()
        self.body_formatter = FixedFormatBodyFormatter()
        self.wrapper = FixedFormatWrapper()
        self.sequence_manager = FixedFormatSequenceManager()
        # conversion_service reads composer.messages after the pass runs.
        self.messages: list[str] = []

    def format(
        self,
        text: str,
        left_start: int | None = None,
        left_step: int | None = None,
        right_start: int | None = None,
        right_step: int | None = None,
        preserve_blank_lines: bool = True,
    ) -> str:
        if not text:
            return ""

        self.messages = []

        lines = self._normalize_line_endings(text).splitlines()
        lines = self._merge_dangling_boolean_lines(lines)

        state = self.sequence_manager.create_state(
            lines=lines,
            left_start=left_start,
            left_step=left_step,
            right_start=right_start,
            right_step=right_step,
        )

        output_lines: list[str] = []
        current_division = ""
        inside_exec_sql = False
        previous_procedure_indent = " "

        for raw_line in lines:
            raw_text = str(raw_line or "").rstrip()

            if not raw_text.strip():
                self._append_blank(state, preserve_blank_lines, output_lines)
                continue

            (
                current_division,
                inside_exec_sql,
                previous_procedure_indent,
            ) = self._compose_body_lines(
                raw_text=raw_text,
                state=state,
                current_division=current_division,
                inside_exec_sql=inside_exec_sql,
                previous_procedure_indent=previous_procedure_indent,
                preserve_blank_lines=preserve_blank_lines,
                output_lines=output_lines,
            )

        return "\n".join(output_lines).rstrip() + "\n"

    def validate_fixed_format(self, text: str) -> list[str]:
        messages: list[str] = []

        for line_number, line in enumerate(
            str(text or "").splitlines(), start=1
        ):
            if not line:
                continue

            if len(line) != TOTAL_WIDTH:
                messages.append(
                    f"Line {line_number}: expected 80 columns, found {len(line)}."
                )
                continue

            left_seq = line[0:6]
            indicator = line[6:7]
            right_seq = line[72:80]

            if not left_seq.isdigit():
                messages.append(
                    f"Line {line_number}: left sequence is not numeric."
                )
            if indicator not in VALID_INDICATORS:
                messages.append(
                    f"Line {line_number}: invalid indicator column value."
                )
            if not right_seq.isdigit():
                messages.append(
                    f"Line {line_number}: right sequence is not numeric."
                )

        return messages

    def _normalize_line_endings(self, text: str) -> str:
        return str(text or "").replace("\r\n", "\n").replace("\r", "\n")

    def _merge_dangling_boolean_lines(self, lines: list[str]) -> list[str]:
        """Join a line ending in AND / OR / NOT to its continuation.

        CORRECTION - the merge had no width check
        ----------------------------------------
        A four-line IF condition reached the generated file as two lines
        cut mid-identifier:

            IF (HELP-DA-CPTAFS-479BFAS < DA-ARCH-YMD  AND HELP-DA-CPTAFS-
               (HELP-DA-CRFMAS-479BFAS < DA-ARCH-YMD AND HELP-DA-CPTAFS-4

        losing "NOT = '00000000') OR" and "= '00000000')" entirely.

        The merge fired whenever the first line ended on a boolean
        operator, regardless of the combined width. 49 + 43 columns were
        joined into a 65-column window and
        replace_body_preserving_sequence sliced the remainder away.

        A merge is now performed ONLY when the result fits columns 8-72.
        When it does not, BOTH lines are left exactly as they were - the
        author's break is already a valid continuation - and the refusal
        is reported. Cosmetic joining must never cost a character.
        """
        output: list[str] = []
        index = 0

        while index < len(lines):
            current = str(lines[index] or "").rstrip()

            if index + 1 >= len(lines):
                output.append(current)
                index += 1
                continue

            next_line = str(lines[index + 1] or "").rstrip()
            current_body = self.line_parser.body_for_boolean_merge(current)
            next_body = self.line_parser.body_for_boolean_merge(next_line)

            if not current_body.strip() or not next_body.strip():
                output.append(current)
                index += 1
                continue
            if self.wrapper.is_comment_or_page_line(current_body):
                output.append(current)
                index += 1
                continue
            if self.wrapper.is_comment_or_page_line(next_body):
                output.append(current)
                index += 1
                continue

            if self.wrapper.ends_with_boolean_operator(current_body):
                merged_body = f"{current_body.rstrip()} {next_body.strip()}"

                if len(merged_body) <= BODY_WIDTH:
                    output.append(
                        self.line_parser.replace_body_preserving_sequence(
                            original_line=current,
                            new_body=merged_body,
                        )
                    )
                    index += 2
                    continue

                # Does not fit. Keep the author's break rather than cut.
                self._log(
                    "merge_refused",
                    width=len(merged_body),
                    limit=BODY_WIDTH,
                    body=current_body.strip()[:40],
                )

            output.append(current)
            index += 1

        return output

    def _log(self, key: str, **values) -> None:
        template = FIXED_FORMAT_MESSAGES.get(key, "")
        if template:
            self.messages.append(template.format(**values))