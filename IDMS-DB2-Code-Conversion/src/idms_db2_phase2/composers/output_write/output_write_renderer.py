# LOCATION: src/idms_db2_phase2/composers/output_write/output_write_renderer.py
# ACTION: CREATE NEW FILE
"""Renders the call site and the extracted write paragraph.

Lines are MOVED and re-indented, never edited: no condition, MOVE or
WRITE is ever rewritten.
"""

from __future__ import annotations

from idms_db2_phase2.composers.output_write.output_write_line_utils import (
    OutputWriteLineUtils,
)
from rules.output_write_paragraph_rules import (
    BLANK_LINE,
    COUNTER_ADD_TEMPLATE,
    EMIT_OUTPUT_COUNTER_INCREMENT,
    EMIT_PAGE_EJECT_BEFORE_PARAGRAPH,
    IND_STATEMENT,
    OUTPUT_COUNTER_NAME,
    PAGE_EJECT_INDICATOR,
    PARAGRAPH_TERMINATOR,
    PERFORM_TEMPLATE,
    WRITE_PARAGRAPH_HEADER_TEMPLATE,
)


class OutputWriteRenderer:
    """Builds the replacement call site and the new paragraph."""

    def __init__(
        self,
        line_utils: OutputWriteLineUtils | None = None,
    ) -> None:
        self.lines = line_utils or OutputWriteLineUtils()

    # ------------------------------------------------------ call site
    def call_site_lines(
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

        return [self.lines.clone(template, body) for body in bodies]

    # ------------------------------------------------------ paragraph
    def paragraph_lines(
        self,
        template: str,
        paragraph: str,
        body: list[str],
    ) -> list[str]:
        out: list[str] = [self.lines.clone(template, BLANK_LINE)]

        if EMIT_PAGE_EJECT_BEFORE_PARAGRAPH:
            out.append(
                self.lines.clone(
                    template,
                    BLANK_LINE,
                    indicator=PAGE_EJECT_INDICATOR,
                )
            )

        out.append(
            self.lines.clone(
                template,
                WRITE_PARAGRAPH_HEADER_TEMPLATE.format(paragraph=paragraph),
            )
        )
        out.extend(self.reindented_body(body))
        return out

    def reindented_body(self, body: list[str]) -> list[str]:
        """Re-anchor the lifted body to Area B, preserving relative depth.

        The block was nested inside two IFs, so every line carries extra
        indent. The shallowest executable line defines the baseline, and
        deeper lines keep their offset from it.
        """
        executable = self.lines.executable_lines(body)
        if not executable:
            return list(body)

        baseline = min(
            len(self.lines.body_indent(line)) for line in executable
        )
        last_index = self.lines.last_executable_index(body)

        out: list[str] = []
        for position, line in enumerate(body):
            text = self.lines.body_text(line)

            if not text or self.lines.is_skippable(line):
                out.append(line)
                continue

            offset = max(len(self.lines.body_indent(line)) - baseline, 0)
            body_text = IND_STATEMENT + (" " * offset) + text

            if position == last_index and not body_text.endswith(
                PARAGRAPH_TERMINATOR
            ):
                body_text = body_text + PARAGRAPH_TERMINATOR

            out.extend(self.lines.replace_body_wrapped(line, body_text))

        return out


__all__ = ["OutputWriteRenderer"]