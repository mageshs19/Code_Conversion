# LOCATION: src/idms_db2_phase2/composers/output_write_paragraph_composer.py
# ACTION: CREATE NEW FILE

"""Output write paragraph composer.

Lifts an inline output-record population block into its own paragraph and
replaces it with a PERFORM, matching the COBOL team's manual reference.

Before:

     HOOFDVERWERKING.
         PERFORM 830-CLOSE-DZEVEFC1
         IF NOT SW-STATUS-D = 'Y'
            IF WS-STATUS = 'C'
               INITIALIZE UITRECORD
               MOVE AM-CNSTK-479BEFF OF DCLDZBEFFTV TO UIT-AM-CN-STOCK
               ...
               WRITE UITRECORD
            END-IF
         END-IF.

After:

     HOOFDVERWERKING.
         PERFORM 830-CLOSE-DZEVEFC1
         IF NOT SW-STATUS-D = 'Y'
            IF WS-STATUS = 'C'
               PERFORM WRITE-UITRECORD
               ADD 1 TO WS-NB-OUTPUT-COUNT
            END-IF
         END-IF.
    /
     WRITE-UITRECORD.
         INITIALIZE UITRECORD
         MOVE AM-CNSTK-479BEFF OF DCLDZBEFFTV TO UIT-AM-CN-STOCK
         ...
         WRITE UITRECORD.

Scope and safety
----------------
- PROCEDURE DIVISION only.
- Extracts only when the block holds exactly ONE WRITE statement. Two
  writes in one guard is a business decision, not a formatting one.
- Never rewrites a condition, a MOVE or the WRITE itself. Lines are moved
  and re-indented, never edited.
- Does nothing when the shape is not recognised, when the target
  paragraph name is already taken, or when the IF has no matching END-IF.
- Comment, page-eject and debug lines are carried along untouched.

Ordering
--------
Must run AFTER composers/cleanup/output_write_placement_cleanup.py (inside
CobolCleanupComposer, wired as composers["feedback_cleanup"]), which
relocates the guarded block from the child-row paragraph into the parent
paragraph. Extracting first would move the block to the wrong home and bake
in the once-per-child-row defect.

Must run AFTER composers["fixed_format"], so generated lines can clone a
real sequence area.

Must run BEFORE FinalSequenceResequencerService, which corrects the cloned
placeholder sequence numbers.

Clean Architecture
------------------
- Every literal lives in rules/output_write_paragraph_rules.py.
- Every regex lives in patterns/output_write_paragraph_patterns.py.
- No program, paragraph, record, table, cursor or host variable name is
  hardcoded.
"""

from __future__ import annotations

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.output_write_paragraph_patterns import (
    DIVISION_PATTERN,
    END_IF_PATTERN,
    IF_START_PATTERN,
    PARAGRAPH_HEADER_PATTERN,
    PERFORM_WRITE_PARAGRAPH_PATTERN,
    PROCEDURE_DIVISION_PATTERN,
    WRITE_STATEMENT_PATTERN,
)
from rules.output_write_paragraph_rules import (
    BLANK_LINE,
    COUNTER_ADD_TEMPLATE,
    EMIT_OUTPUT_COUNTER_INCREMENT,
    EMIT_PAGE_EJECT_BEFORE_PARAGRAPH,
    ENFORCE_OUTPUT_WRITE_PARAGRAPH,
    EXTRACTION_PASS_LIMIT,
    IF_SCAN_LIMIT,
    IND_STATEMENT,
    MINIMUM_BODY_LINES,
    OUTPUT_COUNTER_NAME,
    OUTPUT_WRITE_PARAGRAPH_MESSAGES,
    PAGE_EJECT_INDICATOR,
    PARAGRAPH_TERMINATOR,
    PERFORM_TEMPLATE,
    REQUIRED_WRITE_COUNT,
    SCOPE_TERMINATOR_WORDS,
    WRITE_PARAGRAPH_HEADER_TEMPLATE,
    WRITE_PARAGRAPH_TEMPLATE,
)


class OutputWriteParagraphComposer:
    """Extracts an inline output write block into its own paragraph."""

    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.fixed_format = fixed_format or FixedFormatLineService()
        self.messages: list[str] = []

    # =================================================================
    # Public entry point
    # =================================================================
    def compose(self, text: str) -> str:
        self.messages = []

        if not text or not ENFORCE_OUTPUT_WRITE_PARAGRAPH:
            return str(text or "")

        lines = (
            str(text)
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .split("\n")
        )

        for _pass in range(EXTRACTION_PASS_LIMIT):
            if not self._extract_one_block(lines):
                break

        return "\n".join(lines).rstrip() + "\n"

    # =================================================================
    # One extraction
    # =================================================================
    def _extract_one_block(self, lines: list[str]) -> bool:
        """Find and extract the first eligible block. True when changed."""
        existing = self._paragraph_names(lines)
        procedure_start = self._procedure_division_index(lines)

        if procedure_start < 0:
            return False

        index = procedure_start + 1
        current_paragraph = ""

        while index < len(lines):
            logical = self._logical(lines[index])

            if self._is_division_boundary(logical):
                return False

            header = self._paragraph_name(lines[index])
            if header:
                current_paragraph = header
                index += 1
                continue

            if not IF_START_PATTERN.match(logical):
                index += 1
                continue

            end_index = self._matching_end_if(lines, index)
            if end_index < 0:
                index += 1
                continue

            if self._try_extract(
                lines=lines,
                if_index=index,
                end_index=end_index,
                source_paragraph=current_paragraph,
                existing=existing,
            ):
                return True

            index += 1

        return False

    def _try_extract(
        self,
        lines: list[str],
        if_index: int,
        end_index: int,
        source_paragraph: str,
        existing: set[str],
    ) -> bool:
        body_start = if_index + 1
        body_end = end_index
        body = lines[body_start:body_end]

        writes = self._write_records(body)
        if len(writes) != REQUIRED_WRITE_COUNT:
            if writes:
                self._log(
                    "skipped_multiple_writes",
                    source=source_paragraph or "(unnamed)",
                    count=len(writes),
                )
            return False

        executable = self._executable_lines(body)
        if len(executable) < MINIMUM_BODY_LINES:
            self._log(
                "skipped_too_small",
                source=source_paragraph or "(unnamed)",
            )
            return False

        # Already extracted on an earlier pass.
        if any(
            PERFORM_WRITE_PARAGRAPH_PATTERN.match(self._logical(line))
            for line in body
        ):
            return False

        record = NameNormalizer.to_cobol(writes[0])
        paragraph = WRITE_PARAGRAPH_TEMPLATE.format(record=record)

        if paragraph in existing:
            self._log("skipped_name_taken", paragraph=paragraph)
            return False

        template = self._template_line(lines, if_index)
        call_indent = self._call_indent(lines, body_start)

        replacement = self._call_site_lines(
            template=template,
            indent=call_indent,
            paragraph=paragraph,
        )
        paragraph_block = self._paragraph_lines(
            template=template,
            paragraph=paragraph,
            body=body,
        )

        # Splice the call site in place of the extracted body.
        lines[body_start:body_end] = replacement

        # Append the new paragraph after the source paragraph ends.
        shift = len(replacement) - len(body)
        insert_at = self._paragraph_end_index(lines, end_index + shift)
        lines[insert_at:insert_at] = paragraph_block

        self._log(
            "extracted",
            source=source_paragraph or "(unnamed)",
            paragraph=paragraph,
        )
        if EMIT_OUTPUT_COUNTER_INCREMENT:
            self._log(
                "counter_added",
                counter=OUTPUT_COUNTER_NAME,
                paragraph=paragraph,
            )

        return True

    # =================================================================
    # Rendering
    # =================================================================
    def _call_site_lines(
        self,
        template: str,
        indent: str,
        paragraph: str,
    ) -> list[str]:
        bodies = [indent + PERFORM_TEMPLATE.format(paragraph=paragraph)]

        if EMIT_OUTPUT_COUNTER_INCREMENT:
            bodies.append(
                indent
                + COUNTER_ADD_TEMPLATE.format(name=OUTPUT_COUNTER_NAME)
            )

        return [self._clone(template, body) for body in bodies]

    def _paragraph_lines(
        self,
        template: str,
        paragraph: str,
        body: list[str],
    ) -> list[str]:
        out: list[str] = [self._clone(template, BLANK_LINE)]

        if EMIT_PAGE_EJECT_BEFORE_PARAGRAPH:
            out.append(
                self._clone(
                    template,
                    BLANK_LINE,
                    indicator=PAGE_EJECT_INDICATOR,
                )
            )

        out.append(
            self._clone(
                template,
                WRITE_PARAGRAPH_HEADER_TEMPLATE.format(paragraph=paragraph),
            )
        )
        out.extend(self._reindented_body(body))
        return out

    def _reindented_body(self, body: list[str]) -> list[str]:
        """Re-anchor the lifted body to Area B, preserving relative depth.

        The block was nested inside two IFs, so every line carries extra
        indent. The shallowest executable line defines the baseline, and
        deeper lines keep their offset from it.
        """
        executable = self._executable_lines(body)
        if not executable:
            return list(body)

        baseline = min(
            len(self.fixed_format.body_indent(line)) for line in executable
        )
        last_index = self._last_executable_index(body)

        out: list[str] = []
        for position, line in enumerate(body):
            logical = self.fixed_format.logical(line)

            if not logical:
                out.append(line)
                continue

            if self.fixed_format.is_comment_or_control_line(line):
                out.append(line)
                continue

            offset = max(
                len(self.fixed_format.body_indent(line)) - baseline, 0
            )
            body_text = IND_STATEMENT + (" " * offset) + logical

            if position == last_index and not body_text.endswith(
                PARAGRAPH_TERMINATOR
            ):
                body_text = body_text + PARAGRAPH_TERMINATOR

            out.extend(
                self.fixed_format.replace_body_wrapped(line, body_text)
            )

        return out

    # =================================================================
    # Scanning helpers
    # =================================================================
    def _logical(self, line: str) -> str:
        return self.fixed_format.logical(line).upper()

    def _executable_lines(self, body: list[str]) -> list[str]:
        return [
            line for line in body
            if self.fixed_format.logical(line)
            and not self.fixed_format.is_comment_or_control_line(line)
        ]

    def _paragraph_name(self, line: str) -> str:
        if self.fixed_format.is_comment_or_control_line(line):
            return ""

        match = PARAGRAPH_HEADER_PATTERN.match(self._logical(line))
        if not match:
            return ""

        name = match.group("name").upper()
        if name in SCOPE_TERMINATOR_WORDS or name.startswith("END-"):
            return ""

        return name

    def _paragraph_names(self, lines: list[str]) -> set[str]:
        return {
            name for name in (self._paragraph_name(line) for line in lines)
            if name
        }

    def _procedure_division_index(self, lines: list[str]) -> int:
        for index, line in enumerate(lines):
            if PROCEDURE_DIVISION_PATTERN.match(self._logical(line)):
                return index
        return -1

    @staticmethod
    def _is_division_boundary(logical: str) -> bool:
        return bool(DIVISION_PATTERN.match(logical))

    def _matching_end_if(self, lines: list[str], if_index: int) -> int:
        """Index of the END-IF that closes the IF at if_index."""
        depth = 0
        limit = min(len(lines), if_index + IF_SCAN_LIMIT)

        for index in range(if_index, limit):
            line = lines[index]

            if self.fixed_format.is_comment_or_control_line(line):
                continue

            logical = self._logical(line)
            if not logical:
                continue

            if index > if_index and self._paragraph_name(line):
                return -1

            if IF_START_PATTERN.match(logical):
                depth += 1
                continue

            if END_IF_PATTERN.match(logical):
                depth -= 1
                if depth == 0:
                    return index

        return -1

    def _write_records(self, body: list[str]) -> list[str]:
        out: list[str] = []

        for line in body:
            if self.fixed_format.is_comment_or_control_line(line):
                continue
            match = WRITE_STATEMENT_PATTERN.match(self._logical(line))
            if match:
                out.append(match.group("record"))

        return out

    def _last_executable_index(self, body: list[str]) -> int:
        for index in range(len(body) - 1, -1, -1):
            line = body[index]
            if self.fixed_format.is_comment_or_control_line(line):
                continue
            if self.fixed_format.logical(line):
                return index
        return -1

    def _paragraph_end_index(self, lines: list[str], start: int) -> int:
        """Index just past the paragraph containing `start`."""
        for index in range(start + 1, len(lines)):
            if self._paragraph_name(lines[index]):
                return index
            if self._is_division_boundary(self._logical(lines[index])):
                return index
        return len(lines)

    def _call_indent(self, lines: list[str], body_start: int) -> str:
        for index in range(body_start, len(lines)):
            line = lines[index]
            if self.fixed_format.is_comment_or_control_line(line):
                continue
            if self.fixed_format.logical(line):
                return self.fixed_format.body_indent(line)
        return IND_STATEMENT

    @staticmethod
    def _template_line(lines: list[str], index: int) -> str:
        return lines[index] if 0 <= index < len(lines) else ""

    def _clone(
        self,
        template: str,
        body: str,
        indicator: str | None = None,
    ) -> str:
        """Build a new line borrowing the sequence area of `template`.

        FinalSequenceResequencerService rewrites columns 1-6 and 73-80
        afterwards, so borrowed numbers are placeholders only.
        """
        left, template_indicator, _body, right = self.fixed_format.split(
            template
        )
        marker = (
            indicator if indicator is not None
            else (template_indicator or " ")
        )

        built = self.fixed_format.build_or_none(left, marker, body, right)
        return built if built is not None else body

    # =================================================================
    # Diagnostics
    # =================================================================
    def _log(self, key: str, **values) -> None:
        template = OUTPUT_WRITE_PARAGRAPH_MESSAGES.get(key, "")
        if template:
            self.messages.append(template.format(**values))