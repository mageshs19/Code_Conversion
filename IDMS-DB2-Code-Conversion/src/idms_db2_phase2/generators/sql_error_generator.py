# LOCATION: src/idms_db2_phase2/generators/sql_error_generator.py
# ACTION: REPLACE ENTIRE FILE

"""Generates and ensures the SQLERROR routine.

Generic rule:
- Use SQLERROR, not SQL-ERROR.
- Generated DB2 cursor paragraphs and SQL blocks perform SQLERROR.
- The SQLERROR routine wraps the standard DB2 SQLERROR include.

Generated routine (manual reference layout):

    * SQLERROR ROUTINE.
         EXEC SQL
              INCLUDE SQLERROR
         END-EXEC.

Paragraph-header policy (Decision D-1, CLOSED by the manual reference):
- The SQLERROR copybook supplies the paragraph label itself.
- Emitting a local "SQLERROR." header duplicates that label and the
  compiler rejects the program with a duplicate paragraph-name error.
- code_review/standards/cobol_standards.py records the same decision:
      SQL_ERROR_BODY    = ("EXEC SQL", "INCLUDE SQLERROR", "END-EXEC")
      SQL_ERROR_INCLUDE = "INCLUDE SQLERROR"
  and CHK-05.01 accepts "declared OR included".
- Set EMIT_SQL_ERROR_PARAGRAPH_HEADER = True in rules/sql_error_rules.py
  if a site ever needs the old behaviour back.

COBOL termination rule:
- A period inside EVALUATE terminates the COBOL *sentence*, which closes
  the EVALUATE early and orphans END-EVALUATE (compile error).
- This class therefore renames SQL-ERROR to SQLERROR but NEVER adds,
  moves or removes a period on a PERFORM inside an EVALUATE block. The
  original terminator is captured by the pattern and carried through
  unchanged.

Clean Architecture:
- No regex is defined in this file. Every pattern lives in
  patterns/cursor_paragraph_patterns.py and patterns/db2_patterns.py.
- Every literal lives in rules/sql_error_rules.py.
"""

from __future__ import annotations

import re

from patterns.cursor_paragraph_patterns import (
    LEGACY_SQL_ERROR_HEADER_PATTERN,
    LEGACY_SQL_ERROR_HEADER_REPLACEMENT,
    LEGACY_SQL_ERROR_PERFORM_PATTERN,
)
from patterns.db2_patterns import END_PROGRAM_PATTERN
from patterns.sql_error_patterns import (
    END_PROGRAM_BOUNDARY_PATTERN,
    PARAGRAPH_HEADER_PATTERN,
    SQLERROR_HEADER_ONLY_PATTERN,
    SQLERROR_PARAGRAPH_PATTERN,
)
from rules.sql_error_rules import (
    EMIT_SQL_ERROR_PARAGRAPH_HEADER,
    IND_SQL_BODY,
    IND_STATEMENT,
    OLD_BLOCK_BODY_TOKENS,
    SQL_ERROR_BANNER,
    SQL_ERROR_INCLUDE_NAME,
    SQL_ERROR_MESSAGES,
    SQL_ERROR_PARAGRAPH_NAME,
)

LEFT_SEQUENCE_WIDTH = 6
RIGHT_SEQUENCE_WIDTH = 8
FIXED_LINE_WIDTH = 80


class SqlErrorGenerator:
    """Owns the SQLERROR routine block and legacy-name normalisation."""

    SQLERROR_PARAGRAPH_NAME = SQL_ERROR_PARAGRAPH_NAME

    # Public alias consumed by CursorParagraphGenerator so both generators
    # read the paragraph name from one place and cannot drift apart.
    PARAGRAPH_NAME = SQL_ERROR_PARAGRAPH_NAME
    DEFAULT_PARAGRAPH_NAME = SQL_ERROR_PARAGRAPH_NAME

    # ... existing __init__ and methods unchanged ...

    # -----------------------------------------------------------------
    # Pipeline entry point - DO NOT RENAME
    # -----------------------------------------------------------------
    def ensure_sql_error_paragraph(self, text: str) -> str:
        """Called by orchestration/conversion/conversion_pipeline.py."""
        return self.ensure_paragraph(text)

    SQLERROR_PARAGRAPH_NAME = SQL_ERROR_PARAGRAPH_NAME

    def __init__(self) -> None:
        self.messages: list[str] = []

    # =================================================================
    # Routine block
    # =================================================================
    def paragraph_block(self) -> str:
        """The generated SQLERROR routine as one text block."""
        return "\n".join(self.paragraph_lines())

    def paragraph_lines(self) -> list[str]:
        """The generated SQLERROR routine as body lines.

        Manual reference emits a comment banner and the include only.
        The paragraph label itself comes from the SQLERROR copybook.
        """
        lines: list[str] = [SQL_ERROR_BANNER]

        if EMIT_SQL_ERROR_PARAGRAPH_HEADER:
            lines.append(f"{SQL_ERROR_PARAGRAPH_NAME}.")

        lines.append(f"{IND_STATEMENT}EXEC SQL")
        lines.append(f"{IND_SQL_BODY}INCLUDE {SQL_ERROR_INCLUDE_NAME}")
        lines.append(f"{IND_STATEMENT}END-EXEC.")
        return lines

    # =================================================================
    # Ensure the routine exists exactly once
    # =================================================================
    def ensure_paragraph(self, text: str) -> str:
        """Normalise legacy names, then guarantee one SQLERROR routine."""
        self.messages = []

        output = self.rename_legacy(str(text or ""))
        if not output.strip():
            return output

        # An existing routine is rewritten in place so stale bodies
        # (DISPLAY / CALL USERABEN form) are replaced by the include form.
        if self._has_sqlerror_paragraph(output):
            output = self._replace_existing_sqlerror_paragraph(output)
            self.messages.append(SQL_ERROR_MESSAGES["routine_replaced"])
            return output

        if self._has_sqlerror_include(output):
            self.messages.append(SQL_ERROR_MESSAGES["already_present"])
            return output

        output = self._append_routine(output)
        self.messages.append(SQL_ERROR_MESSAGES["routine_added"])
        return output

    # Backward-compatible alias for existing callers.
    def ensure(self, text: str) -> str:
        return self.ensure_paragraph(text)

    def _append_routine(self, text: str) -> str:
        block = self.paragraph_block()
        match = END_PROGRAM_PATTERN.search(text)

        if match:
            insert_at = match.start()
            return f"{text[:insert_at]}\n{block}\n{text[insert_at:]}"

        return f"{text.rstrip()}\n\n{block}\n"

    # =================================================================
    # Legacy SQL-ERROR -> SQLERROR
    # =================================================================
    def rename_legacy(self, text: str) -> str:
        """Rename SQL-ERROR to SQLERROR without touching terminators."""
        output = str(text or "")
        if not output:
            return output

        # A paragraph header always ends in a period, so this rename is
        # safe and the replacement re-supplies the period.
        output, header_count = LEGACY_SQL_ERROR_HEADER_PATTERN.subn(
            LEGACY_SQL_ERROR_HEADER_REPLACEMENT,
            output,
        )

        # The PERFORM terminator is captured and carried through. A fixed
        # "PERFORM SQLERROR." substitution would add a period to a
        # statement inside EVALUATE and orphan END-EVALUATE.
        def _perform(match: re.Match) -> str:
            dot = match.group("dot") or ""
            return f"PERFORM {SQL_ERROR_PARAGRAPH_NAME}{dot}"

        output, perform_count = LEGACY_SQL_ERROR_PERFORM_PATTERN.subn(
            _perform,
            output,
        )

        if header_count or perform_count:
            self.messages.append(
                SQL_ERROR_MESSAGES["renamed_legacy"].format(
                    headers=header_count,
                    performs=perform_count,
                )
            )

        return output

    # =================================================================
    # Detection
    # =================================================================
    def _has_sqlerror_paragraph(self, text: str) -> bool:
        return bool(SQLERROR_PARAGRAPH_PATTERN.search(str(text or "")))

    @staticmethod
    def _has_sqlerror_include(text: str) -> bool:
        return f"INCLUDE {SQL_ERROR_INCLUDE_NAME}".upper() in str(
            text or ""
        ).upper()

    def _is_sqlerror_paragraph_header(self, line: str) -> bool:
        logical = self._logical_line(line)
        return bool(SQLERROR_HEADER_ONLY_PATTERN.fullmatch(logical))

    def _is_next_paragraph_or_program_boundary(self, line: str) -> bool:
        """True when the scan has run past the old SQLERROR body."""
        logical = self._logical_line(line)
        if not logical:
            return False
        if END_PROGRAM_BOUNDARY_PATTERN.match(logical):
            return True
        return bool(PARAGRAPH_HEADER_PATTERN.fullmatch(logical))

    def _line_belongs_to_old_sqlerror_block(self, line: str) -> bool:
        """True for a body line of a previously generated SQLERROR block."""
        logical = self._logical_line(line).upper()
        if not logical:
            return False
        return any(token in logical for token in OLD_BLOCK_BODY_TOKENS)

    # =================================================================
    # In-place replacement of an existing routine
    # =================================================================
    def _replace_existing_sqlerror_paragraph(self, text: str) -> str:
        """Swap any existing SQLERROR body for the generated routine."""
        lines = str(text or "").splitlines()
        output: list[str] = []
        index = 0
        replaced = False

        while index < len(lines):
            line = lines[index]

            if not self._is_sqlerror_paragraph_header(line):
                output.append(line)
                index += 1
                continue

            output.extend(self.paragraph_lines())
            replaced = True
            index += 1

            # Consume the old body: generated body lines and blank lines
            # only. Stop at the next paragraph header or END PROGRAM.
            while index < len(lines):
                current = lines[index]

                if self._is_next_paragraph_or_program_boundary(current):
                    break
                if self._line_belongs_to_old_sqlerror_block(current):
                    index += 1
                    continue
                if not current.strip():
                    index += 1
                    continue
                break

        if not replaced:
            return text

        return "\n".join(output).rstrip() + "\n"

    # =================================================================
    # Fixed-format helpers
    # =================================================================
    @staticmethod
    def _logical_line(line: str) -> str:
        """Strip sequence numbers and the indicator, return the body."""
        text = str(line or "").rstrip("\n").rstrip()
        if not text:
            return ""

        if (
            len(text) >= FIXED_LINE_WIDTH
            and text[:LEFT_SEQUENCE_WIDTH].isdigit()
            and text[
                FIXED_LINE_WIDTH - RIGHT_SEQUENCE_WIDTH : FIXED_LINE_WIDTH
            ].isdigit()
        ):
            return text[
                LEFT_SEQUENCE_WIDTH + 1 : FIXED_LINE_WIDTH - RIGHT_SEQUENCE_WIDTH
            ].strip()

        if text[:LEFT_SEQUENCE_WIDTH].isdigit():
            return text[LEFT_SEQUENCE_WIDTH:].strip()

        return text.strip()