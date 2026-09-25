# LOCATION: src/idms_db2_phase2/composers/retrieval_commit_cleanup_composer.py
# ACTION: REPLACE ENTIRE FILE
"""Removes a COMMIT block from a retrieval program.

Safety net only. ControlStatementConverter is the authority and now
honours EMIT_COMMIT_IN_RETRIEVAL. This pass catches a COMMIT that
arrives by any other route: one already present in the legacy source, or
one emitted by a generator that does not read the flag.

Scope and safety
  - PROCEDURE DIVISION only.
  - Runs ONLY when the program is retrieval.
  - Removes the whole EXEC SQL ... COMMIT ... END-EXEC block plus the
    MOVE 'COMMIT' TO SQL-LOCATION line that precedes it.
  - Leaves a comment so the removal is visible, never silent.
  - Does nothing at all when the shape is not recognised.

CORRECTION 1 - the removal could empty a paragraph
----------------------------------------------------
The replacement is a COMMENT, which is not executable. In one converted
program the paragraph survived only because a CLOSE followed:

    <paragraph>.
    * DB2: COMMIT removed; retrieval program is read-only.
        CLOSE <file>.                <- rescued it

A paragraph containing ONLY the COMMIT block would have been left with a
comment and nothing else, and the compiler rejects an empty paragraph.
The pass now looks FORWARD for the next executable statement and emits
CONTINUE. when it meets a paragraph, section or division boundary first.

CORRECTION 2 - a short record flipped a boundary decision
-----------------------------------------------------------
strip_sequence_numbers() recognises a right sequence only in columns
73-80 of a FULL 80-column record. A line short by even one character
keeps its trailing digits, so a paragraph header read as

    <paragraph>.                             0074700

which contains a space and was therefore classified as a STATEMENT. The
emptiness scan then concluded the paragraph was still populated and the
guard never fired. _logical() now drops a trailing sequence-length digit
run defensively.

CORRECTION 3 - the generated record was 79 columns
----------------------------------------------------
The rendered body carries the indicator, so it spans columns 7-72, which
is 66 characters, not 65. At 65 the record came out one column short and
the right sequence landed in column 72.

The widths are now DERIVED from the column boundaries rather than
written as separate literals, so the three cannot drift apart.

No program, record, table, cursor, paragraph or host variable name is
hardcoded. Constants live in rules/retrieval_commit_cleanup_rules.py.
"""

from __future__ import annotations

from patterns.sequence_patterns import strip_sequence_numbers
from rules.retrieval_commit_cleanup_rules import (
    BLOCK_SCAN_LIMIT,
    COMMIT_LOCATION_TOKEN,
    COMMIT_REMOVED_COMMENT,
    COMMIT_SQL_TOKEN,
    CONTINUE_INDENT,
    CONTINUE_INDICATOR,
    CONTINUE_STATEMENT,
    EMPTINESS_SCAN_LIMIT,
    END_EXEC_TOKEN,
    ENFORCE_PARAGRAPH_NOT_EMPTIED,
    ENFORCE_RETRIEVAL_COMMIT_CLEANUP,
    EXEC_SQL_TOKEN,
    NON_PARAGRAPH_SINGLE_WORDS,
    RETRIEVAL_COMMIT_MESSAGES,
)

# ---------------------------------------------------------------------
# Fixed-format geometry
#
#     columns  1-6   left sequence
#     column   7     indicator
#     columns  8-72  body
#     columns 73-80  right sequence
#
# A rendered line carries the indicator INSIDE its body string, so the
# written span is columns 7-72. Every width below is derived from the
# two boundaries, so they cannot drift apart.
# ---------------------------------------------------------------------
LEFT_SEQUENCE_WIDTH = 6
RIGHT_SEQUENCE_START = 72
RIGHT_SEQUENCE_END = 80

INDICATOR_AND_BODY_WIDTH = RIGHT_SEQUENCE_START - LEFT_SEQUENCE_WIDTH
FIXED_LINE_WIDTH = RIGHT_SEQUENCE_END

# A trailing digit run at least this long is a sequence number, never a
# COBOL numeric literal. Seven is the floor so "IF X = 100" is safe.
RIGHT_SEQUENCE_DIGIT_FLOOR = 7

COMMENT_INDICATORS = ("*", "/")
DIVISION_TOKEN = "DIVISION"
SECTION_TOKEN = "SECTION."
STATEMENT_TERMINATOR = "."
WORD_SEPARATOR = " "


class RetrievalCommitCleanupComposer:
    """Strips COMMIT from a read-only program."""

    def __init__(self, *, is_update_program: bool = False) -> None:
        self.is_update_program = bool(is_update_program)
        self.messages: list[str] = []

    # =================================================================
    # Public entry point
    # =================================================================
    def compose(self, text: str) -> str:
        self.messages = []

        if not text or not ENFORCE_RETRIEVAL_COMMIT_CLEANUP:
            return text or ""

        if self.is_update_program:
            self._log("kept_update")
            return text

        lines = self._split(text)
        output: list[str] = []
        index = 0
        removed = 0

        while index < len(lines):
            span = self._commit_span(lines, index)

            if span < 0:
                output.append(lines[index])
                index += 1
                continue

            template = lines[index]
            output.append(self._comment_like(template))

            # The comment is not executable. If the removed block was
            # the paragraph's only statement, the paragraph no longer
            # compiles, so CONTINUE. goes in alongside it.
            if ENFORCE_PARAGRAPH_NOT_EMPTIED and self._paragraph_emptied(
                lines,
                span,
            ):
                output.append(self._continue_like(template))
                self._log("continue_added")

            index = span
            removed += 1

        if removed:
            self._log("removed", count=removed)
        else:
            self._log("none_found")

        return "\n".join(output)

    # =================================================================
    # Block detection
    # =================================================================
    def _commit_span(self, lines: list[str], start: int) -> int:
        """Index AFTER the COMMIT block starting at `start`, or -1."""
        body = self._logical(lines[start])

        # Form A: MOVE 'COMMIT' TO SQL-LOCATION, then the EXEC block.
        if COMMIT_SQL_TOKEN in body and COMMIT_LOCATION_TOKEN in body:
            end = self._exec_block_end(lines, start + 1)
            return end if end > 0 else start + 1

        # Form B: a bare EXEC SQL COMMIT END-EXEC block.
        if body.startswith(EXEC_SQL_TOKEN):
            end = self._exec_block_end(lines, start)
            if end > 0 and self._block_is_commit(lines, start, end):
                return end

        return -1

    def _exec_block_end(self, lines: list[str], start: int) -> int:
        """Index AFTER END-EXEC, or -1 when the block does not close."""
        if start >= len(lines):
            return -1
        if not self._logical(lines[start]).startswith(EXEC_SQL_TOKEN):
            return -1

        limit = min(start + BLOCK_SCAN_LIMIT, len(lines))
        for index in range(start, limit):
            if END_EXEC_TOKEN in self._logical(lines[index]):
                return index + 1
        return -1

    def _block_is_commit(self, lines: list[str], start: int, end: int) -> bool:
        return any(
            self._logical(lines[index]).startswith(COMMIT_SQL_TOKEN)
            for index in range(start, end)
        )

    # =================================================================
    # Paragraph emptiness
    # =================================================================
    def _paragraph_emptied(self, lines: list[str], start: int) -> bool:
        """True when no executable statement follows before the next
        paragraph, section or division boundary.

        Scans FORWARD only. A statement BEFORE the removed block would
        already keep the paragraph valid, and in that case this returns
        False on the first executable line it meets after the block
        anyway - so looking backwards adds nothing and risks crossing
        into the previous paragraph.
        """
        scanned = 0

        for index in range(start, len(lines)):
            if scanned >= EMPTINESS_SCAN_LIMIT:
                # Lost sync. Stand down rather than inject a CONTINUE
                # that may not belong.
                return False
            scanned += 1

            body = self._logical(lines[index])

            if not body:
                continue

            if body.startswith(COMMENT_INDICATORS):
                continue

            if self._is_boundary(body):
                # Next paragraph reached with nothing executable in
                # between: the paragraph is empty.
                return True

            # Any other logical line is an executable statement.
            return False

        # End of program with nothing executable after the removal.
        return True

    @staticmethod
    def _is_boundary(body: str) -> bool:
        """A paragraph header, section header or division boundary."""
        text = str(body or "").strip().upper()
        if not text:
            return False

        if DIVISION_TOKEN in text and text.endswith(STATEMENT_TERMINATOR):
            return True

        if text.endswith(SECTION_TOKEN):
            return True

        # A single word ending in a period is a paragraph header unless
        # it is a scope terminator such as EXIT. or GOBACK.
        if WORD_SEPARATOR not in text and text.endswith(STATEMENT_TERMINATOR):
            word = text.rstrip(STATEMENT_TERMINATOR)
            return bool(word) and word not in NON_PARAGRAPH_SINGLE_WORDS

        return False

    # =================================================================
    # Line rendering
    # =================================================================
    def _comment_like(self, line: str) -> str:
        """The removal comment, carrying the sequence area of `line`."""
        return self._render(line, COMMIT_REMOVED_COMMENT)

    def _continue_like(self, line: str) -> str:
        """CONTINUE. carrying the sequence area of `line`.

        The indicator column is blank and the statement starts at
        column 12, which is where an Area B statement belongs.
        """
        return self._render(
            line,
            CONTINUE_INDICATOR + CONTINUE_INDENT + CONTINUE_STATEMENT,
        )

    @staticmethod
    def _render(line: str, body: str) -> str:
        """One fixed-format record carrying `body`.

        The sequence areas of the template line are preserved, so the
        generated line sits in the same columns as the line it replaces.
        A template that is not fixed-format yields the bare body, which
        a later formatting pass will sequence.
        """
        text = str(line or "")

        is_fixed = (
            len(text) > LEFT_SEQUENCE_WIDTH
            and text[:LEFT_SEQUENCE_WIDTH].strip().isdigit()
        )
        if not is_fixed:
            return body

        left = text[:LEFT_SEQUENCE_WIDTH]
        right = (
            text[RIGHT_SEQUENCE_START:RIGHT_SEQUENCE_END]
            if len(text) >= FIXED_LINE_WIDTH
            else ""
        )
        written = body[:INDICATOR_AND_BODY_WIDTH].ljust(
            INDICATOR_AND_BODY_WIDTH
        )

        return f"{left}{written}{right}"

    # =================================================================
    # Helpers
    # =================================================================
    @staticmethod
    def _split(text: str) -> list[str]:
        """Line list, tolerant of CRLF and lone-CR line endings."""
        return (
            str(text or "")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .split("\n")
        )

    @staticmethod
    def _logical(line: str) -> str:
        """Uppercased logical line, sequence areas removed.

        DEFENCE - strip_sequence_numbers() recognises a right sequence
        only in columns 73-80 of a FULL 80-column record. A line short by
        even one character keeps its trailing digits, and a paragraph
        header then reads as

            <paragraph>.                             0074700

        which contains a space and is classified as a statement. A
        trailing run of RIGHT_SEQUENCE_DIGIT_FLOOR or more digits is a
        sequence number, not COBOL, so it is dropped.
        """
        text = str(strip_sequence_numbers(str(line or "")) or "").strip().upper()

        parts = text.rsplit(WORD_SEPARATOR, 1)
        if (
            len(parts) == 2
            and parts[1].isdigit()
            and len(parts[1]) >= RIGHT_SEQUENCE_DIGIT_FLOOR
        ):
            text = parts[0].rstrip()

        return text

    def _log(self, key: str, **values) -> None:
        template = RETRIEVAL_COMMIT_MESSAGES.get(key, "")
        if template:
            self.messages.append(template.format(**values))


__all__ = ["RetrievalCommitCleanupComposer"]