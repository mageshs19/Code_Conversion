"""Output write placement cleanup.

An IDMS child-set loop converts to:

    PERFORM <open-child>
    PERFORM <fetch-child> UNTIL <eoc> OR SW-STATUS-D = 'Y'
    PERFORM <close-child>

The per-row paragraph performed from the child FETCH paragraph decides the
row status only. A guarded output WRITE belongs in the PARENT paragraph,
after the child cursor has been closed, because the decision is not final
until every child row has been seen.

Left inside the per-row paragraph, a guarded WRITE fires again for every
later matching child row and multiplies the output file.

Manual reference shape produced by this pass:

    PERFORM <close-child>

    IF NOT SW-STATUS-D = 'Y'
       IF <status-field> = '<value>'
          PERFORM <write-paragraph>
       END-IF
    END-IF

This pass moves lines only. It never rewrites a condition, a MOVE or a
WRITE, and it does nothing at all when the shape is not recognised:

  1. locate child FETCH paragraphs (number >= CHILD_FETCH_MINIMUM_NUMBER),
  2. locate the row paragraph each one performs under WHEN ZERO,
  3. locate the PERFORM <nnn>-CLOSE-<cursor> line in the parent paragraph,
  4. lift a trailing IF ... WRITE ... END-IF block out of the row paragraph,
  5. re-indent it and insert it after the child CLOSE, wrapped in the
     early-stop guard when the parent loop uses the early-stop flag.

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
    END_IF_PATTERN,
    FETCH_PARAGRAPH_NUMBER_PATTERN,
    IF_START_PATTERN,
    PARAGRAPH_HEADER_PATTERN,
    PERFORM_CLOSE_CURSOR_PATTERN,
    PERFORM_CURSOR_PARAGRAPH_PATTERN,
    PERFORM_PARAGRAPH_PATTERN,
    WHEN_ZERO_PATTERN,
    WRITE_STATEMENT_PATTERN,
)
from rules.cobol_cleanup_rules import (
    CHILD_FETCH_MINIMUM_NUMBER,
    EARLY_STOP_FLAG,
    EARLY_STOP_GUARD_CLOSE,
    EARLY_STOP_GUARD_OPEN,
    EARLY_STOP_VALUE,
    ENFORCE_OUTPUT_WRITE_AFTER_CHILD_LOOP,
    FETCH_PARAGRAPH_CURSOR_SEPARATOR,
    NESTED_INDENT_STEP,
    NON_PARAGRAPH_SINGLE_WORDS,
    OUTPUT_WRITE_MOVE_PASS_LIMIT,
    WHEN_ZERO_PERFORM_SCAN_LIMIT,
)


class OutputWritePlacementCleanup:
    """Moves a guarded output write out of a child-row paragraph."""

    def __init__(
        self,
        messages: CleanupMessageCollector,
        line_utils: CobolCleanupLineUtils | None = None,
    ) -> None:
        self.messages = messages
        self.line_utils = line_utils or CobolCleanupLineUtils()

    def _logical(self, line: str) -> str:
        return self.line_utils.logical(line)

    def _leading_spaces(self, line: str) -> str:
        return self.line_utils.leading_spaces(line)

    def _is_comment_or_blank(self, logical: str) -> bool:
        return self.line_utils.is_comment_or_blank(logical)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def move_output_write_after_child_loop(self, text: str) -> str:
        """Relocate every misplaced guarded output write block."""
        if not text or not ENFORCE_OUTPUT_WRITE_AFTER_CHILD_LOOP:
            return text or ""

        lines = (
            str(text)
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .split("\n")
        )

        for _pass in range(OUTPUT_WRITE_MOVE_PASS_LIMIT):
            moved = self._move_one_block(lines)
            if not moved:
                break

        return "\n".join(lines).rstrip() + "\n"

    # ------------------------------------------------------------------
    # One relocation
    # ------------------------------------------------------------------
    def _move_one_block(self, lines: list[str]) -> bool:
        """Move at most one block. Returns True when the list was changed."""
        spans = self._paragraph_spans(lines)
        if not spans:
            return False

        for fetch_paragraph, fetch_span in spans.items():
            if not self._is_child_fetch(fetch_paragraph):
                continue

            row_paragraph = self._row_paragraph(lines, fetch_span)
            if not row_paragraph or row_paragraph not in spans:
                continue

            cursor = self._cursor_of(fetch_paragraph)
            if not cursor:
                continue

            close_index = self._close_perform_index(
                lines=lines,
                spans=spans,
                cursor=cursor,
            )
            if close_index < 0:
                continue

            block = self._trailing_write_block(lines, spans[row_paragraph])
            if not block:
                continue

            start, end = block

            if self._index_in_span(close_index, (start, end)):
                continue

            self._relocate(
                lines=lines,
                start=start,
                end=end,
                close_index=close_index,
            )

            self.messages.add(
                "output_write_moved",
                source=row_paragraph,
                target=self._owner_paragraph(spans, close_index),
            )
            return True

        return False

    def _relocate(
        self,
        lines: list[str],
        start: int,
        end: int,
        close_index: int,
    ) -> None:
        block = lines[start : end + 1]
        base_indent = self._leading_spaces(lines[close_index])
        guarded = self._uses_early_stop(lines, close_index)

        rendered = self._render(
            block=block,
            base_indent=base_indent,
            guarded=guarded,
        )

        del lines[start : end + 1]

        removed = end - start + 1
        anchor = close_index if close_index < start else close_index - removed

        lines[anchor + 1 : anchor + 1] = rendered

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _render(
        self,
        block: list[str],
        base_indent: str,
        guarded: bool,
    ) -> list[str]:
        """Re-indent the block and optionally wrap it in the early-stop guard."""
        body_indent = (
            base_indent + NESTED_INDENT_STEP if guarded else base_indent
        )
        shifted = self._shift_indent(block, body_indent)

        if not guarded:
            return [""] + shifted

        guard_open = EARLY_STOP_GUARD_OPEN.format(
            flag=EARLY_STOP_FLAG,
            value=EARLY_STOP_VALUE,
        )

        return (
            [""]
            + [f"{base_indent}{guard_open}"]
            + shifted
            + [f"{base_indent}{EARLY_STOP_GUARD_CLOSE}"]
        )

    def _shift_indent(
        self,
        block: list[str],
        target_indent: str,
    ) -> list[str]:
        """Re-indent a block, preserving its internal nesting."""
        original = self._minimum_indent(block)
        output: list[str] = []

        for line in block:
            logical = self._logical(line)

            if not logical:
                output.append("")
                continue

            current = self._leading_spaces(self._body_of(line))
            extra = current[len(original) :] if len(current) > len(original) else ""
            output.append(f"{target_indent}{extra}{logical}")

        return output

    def _minimum_indent(self, block: list[str]) -> str:
        widest = None

        for line in block:
            logical = self._logical(line)
            if not logical:
                continue
            indent = self._leading_spaces(self._body_of(line))
            if widest is None or len(indent) < len(widest):
                widest = indent

        return widest or ""

    def _body_of(self, line: str) -> str:
        """The line with sequence numbers stripped but indentation kept."""
        text = str(line or "").rstrip()
        logical = self._logical(text)

        if not logical:
            return ""

        position = text.find(logical)
        return text[position - self._indent_width(text, position) : ] if False else (
            text[:position].replace("\t", " ")[-self._indent_width(text, position) :]
            + logical
            if position > 0
            else logical
        )

    @staticmethod
    def _indent_width(text: str, position: int) -> int:
        prefix = text[:position]
        return len(prefix) - len(prefix.rstrip(" "))

    # ------------------------------------------------------------------
    # Paragraph discovery
    # ------------------------------------------------------------------
    def _paragraph_spans(self, lines: list[str]) -> dict[str, tuple[int, int]]:
        """Paragraph name -> (first line index, last line index)."""
        spans: dict[str, tuple[int, int]] = {}
        current = ""
        start = -1

        for index, line in enumerate(lines):
            logical = self._logical(line)

            if self._is_comment_or_blank(logical):
                continue

            if not self._is_paragraph_header(logical):
                continue

            if current:
                spans[current] = (start, index - 1)

            current = logical.rstrip(".").upper()
            start = index

        if current and start >= 0:
            spans[current] = (start, len(lines) - 1)

        return spans

    def _is_paragraph_header(self, logical: str) -> bool:
        text = str(logical or "").strip()

        if not text.endswith("."):
            return False

        if not PARAGRAPH_HEADER_PATTERN.match(text):
            return False

        word = text.rstrip(".").upper()
        return bool(word) and word not in NON_PARAGRAPH_SINGLE_WORDS

    def _owner_paragraph(
        self,
        spans: dict[str, tuple[int, int]],
        index: int,
    ) -> str:
        for name, span in spans.items():
            if self._index_in_span(index, span):
                return name
        return "(unnamed)"

    @staticmethod
    def _index_in_span(index: int, span: tuple[int, int]) -> bool:
        start, end = span
        return start <= index <= end

    # ------------------------------------------------------------------
    # Cursor correlation
    # ------------------------------------------------------------------
    def _is_child_fetch(self, paragraph: str) -> bool:
        match = FETCH_PARAGRAPH_NUMBER_PATTERN.match(str(paragraph or "").upper())

        if not match:
            return False

        try:
            number = int(match.group("number"))
        except ValueError:
            return False

        return number >= CHILD_FETCH_MINIMUM_NUMBER

    @staticmethod
    def _cursor_of(paragraph: str) -> str:
        text = str(paragraph or "").upper()
        separator = FETCH_PARAGRAPH_CURSOR_SEPARATOR

        if separator not in text:
            return ""

        return text.split(separator, 1)[1].strip()

    def _row_paragraph(
        self,
        lines: list[str],
        fetch_span: tuple[int, int],
    ) -> str:
        """The business paragraph performed under WHEN ZERO of a FETCH."""
        start, end = fetch_span
        seen_when_zero = False
        scanned = 0

        for index in range(start + 1, min(end + 1, len(lines))):
            logical = self._logical(lines[index])

            if self._is_comment_or_blank(logical):
                continue

            if WHEN_ZERO_PATTERN.match(logical):
                seen_when_zero = True
                scanned = 0
                continue

            if not seen_when_zero:
                continue

            scanned += 1
            if scanned > WHEN_ZERO_PERFORM_SCAN_LIMIT:
                return ""

            if PERFORM_CURSOR_PARAGRAPH_PATTERN.match(logical):
                continue

            match = PERFORM_PARAGRAPH_PATTERN.match(logical)
            if match:
                return match.group("paragraph").upper()

        return ""

    def _close_perform_index(
        self,
        lines: list[str],
        spans: dict[str, tuple[int, int]],
        cursor: str,
    ) -> int:
        """Index of PERFORM <nnn>-CLOSE-<cursor> in a non-cursor paragraph."""
        for index, line in enumerate(lines):
            logical = self._logical(line)

            match = PERFORM_CLOSE_CURSOR_PATTERN.match(logical)
            if not match:
                continue

            if match.group("cursor").upper() != cursor:
                continue

            owner = self._owner_paragraph(spans, index)
            if self._is_generated_cursor_paragraph(owner):
                continue

            return index

        return -1

    def _is_generated_cursor_paragraph(self, paragraph: str) -> bool:
        return bool(
            FETCH_PARAGRAPH_NUMBER_PATTERN.match(str(paragraph or "").upper())
        )

    def _uses_early_stop(self, lines: list[str], close_index: int) -> bool:
        """True when the loop above the CLOSE uses the early-stop flag."""
        for index in range(close_index - 1, -1, -1):
            logical = self._logical(lines[index]).upper()

            if self._is_comment_or_blank(logical):
                continue

            if EARLY_STOP_FLAG in logical:
                return True

            if self._is_paragraph_header(logical):
                return False

        return False

    # ------------------------------------------------------------------
    # Write block discovery
    # ------------------------------------------------------------------
    def _trailing_write_block(
        self,
        lines: list[str],
        span: tuple[int, int],
    ) -> tuple[int, int] | None:
        """The last IF ... WRITE ... END-IF construct of a paragraph."""
        start, end = span

        last = self._last_code_index(lines, start, end)
        if last < 0:
            return None

        if not END_IF_PATTERN.match(self._logical(lines[last])):
            return None

        opener = self._matching_if_index(lines, start, last)
        if opener < 0:
            return None

        block = lines[opener : last + 1]

        if not any(
            WRITE_STATEMENT_PATTERN.match(self._logical(line)) for line in block
        ):
            return None

        if any(
            PERFORM_CURSOR_PARAGRAPH_PATTERN.match(self._logical(line))
            for line in block
        ):
            return None

        return opener, last

    def _last_code_index(
        self,
        lines: list[str],
        start: int,
        end: int,
    ) -> int:
        for index in range(min(end, len(lines) - 1), start, -1):
            logical = self._logical(lines[index])
            if self._is_comment_or_blank(logical):
                continue
            return index
        return -1

    def _matching_if_index(
        self,
        lines: list[str],
        start: int,
        end_if_index: int,
    ) -> int:
        """Walk back from an END-IF to its own IF, honouring nesting."""
        depth = 0

        for index in range(end_if_index, start, -1):
            logical = self._logical(lines[index])

            if self._is_comment_or_blank(logical):
                continue

            if END_IF_PATTERN.match(logical):
                depth += 1
                continue

            if IF_START_PATTERN.match(logical):
                depth -= 1
                if depth == 0:
                    return index

        return -1