# LOCATION: src/idms_db2_phase2/composers/cleanup/paragraph_terminator_cleanup.py
# ACTION: REPLACE ENTIRE FILE

"""
Paragraph sentence termination cleanup.

A COBOL paragraph is one or more sentences. When an earlier cleanup pass
inserts or lifts a block, the paragraph can be left ending on a bare scope
terminator:

    WRITE UITRECORD
    END-IF                  <- no period
    /
    710-OPEN-DZBEFFC1.

The sentence then runs into the next paragraph header and the compiler
rejects the program.

This pass finds the last executable line of every paragraph in the
PROCEDURE DIVISION and appends the sentence terminator when it is missing.
Comment, page-eject and blank lines are skipped, and a line that already
ends the sentence is never touched.

Runs last in CobolCleanupComposer, so it also covers blocks relocated by
OutputWritePlacementCleanup.

No program, paragraph, record, table, cursor or host variable name is
hardcoded. Regex lives in patterns/cobol_cleanup_patterns.py, constants in
rules/cobol_cleanup_rules.py.
"""

from idms_db2_phase2.composers.cleanup.cleanup_message_collector import (
    CleanupMessageCollector,
)
from idms_db2_phase2.composers.cleanup.cobol_cleanup_line_utils import (
    CobolCleanupLineUtils,
)
from patterns.cobol_cleanup_patterns import (
    PARAGRAPH_HEADER_PATTERN,
    PROCEDURE_DIVISION_LINE_PATTERN,
    SECTION_HEADER_PATTERN,
)
from patterns.sequence_patterns import strip_sequence_numbers
from rules.cobol_cleanup_rules import (
    ENFORCE_PARAGRAPH_TERMINATION,
    NON_PARAGRAPH_SINGLE_WORDS,
    PARAGRAPH_TERMINATOR,
)


class ParagraphTerminatorCleanup:
    def __init__(
        self,
        messages: CleanupMessageCollector,
        line_utils: CobolCleanupLineUtils | None = None,
    ) -> None:
        self.messages = messages
        self.line_utils = line_utils or CobolCleanupLineUtils()

    def _logical(self, line: str) -> str:
        return self.line_utils.logical(line)

    def _is_comment_or_blank(self, logical: str) -> bool:
        return self.line_utils.is_comment_or_blank(logical)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def ensure_paragraph_termination(self, text: str) -> str:
        if not text or not ENFORCE_PARAGRAPH_TERMINATION:
            return text or ""

        lines = (
            str(text)
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .split("\n")
        )

        procedure_index = self._procedure_division_index(lines)
        if procedure_index < 0:
            return text

        output = list(lines)
        current_paragraph = ""
        last_code_index = -1
        changed = False

        for index in range(procedure_index + 1, len(output)):
            logical = self._logical(output[index])

            if self._is_comment_or_blank(logical):
                continue

            if self._is_paragraph_header(logical):
                changed = (
                    self._terminate(output, last_code_index, current_paragraph)
                    or changed
                )
                current_paragraph = logical.rstrip(PARAGRAPH_TERMINATOR)
                last_code_index = -1
                continue

            last_code_index = index

        # Close the final paragraph of the program.
        changed = (
            self._terminate(output, last_code_index, current_paragraph)
            or changed
        )

        if not changed:
            return text

        return "\n".join(output).rstrip() + "\n"

    # ------------------------------------------------------------------
    # Termination
    # ------------------------------------------------------------------
    def _terminate(
        self,
        output: list[str],
        index: int,
        paragraph: str,
    ) -> bool:
        """Append the sentence terminator when it is missing."""
        if index < 0:
            return False

        line = output[index]
        logical = self._logical(line)

        if not logical:
            return False

        if logical.endswith(PARAGRAPH_TERMINATOR):
            return False

        body = strip_sequence_numbers(str(line or "")).rstrip()

        if not body.strip():
            return False

        output[index] = body + PARAGRAPH_TERMINATOR

        self.messages.add(
            "paragraph_terminated",
            paragraph=paragraph or "(unnamed)",
        )
        return True

    # ------------------------------------------------------------------
    # Structure detection
    # ------------------------------------------------------------------
    def _is_paragraph_header(self, logical: str) -> bool:
        text = str(logical or "").strip()

        if not text.endswith(PARAGRAPH_TERMINATOR):
            return False

        if SECTION_HEADER_PATTERN.match(text):
            return True

        if not PARAGRAPH_HEADER_PATTERN.match(text):
            return False

        word = text.rstrip(PARAGRAPH_TERMINATOR).upper()
        return bool(word) and word not in NON_PARAGRAPH_SINGLE_WORDS

    def _procedure_division_index(self, lines: list[str]) -> int:
        for index, line in enumerate(lines):
            logical = self._logical(line)

            if self._is_comment_or_blank(logical):
                continue

            if PROCEDURE_DIVISION_LINE_PATTERN.match(logical):
                return index

        return -1