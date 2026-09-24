# LOCATION: src/idms_db2_phase2/composers/output_write/output_write_extractor.py
# ACTION: CREATE NEW FILE
"""Performs one accepted extraction.

Lines are MOVED and re-indented, never edited: no condition, MOVE or
WRITE is ever rewritten. Two splices happen, in this order:

    1 the guarded body is replaced by the call site,
    2 the new paragraph is inserted after the host paragraph ends.

The second index must be corrected for the size change the first splice
caused, which is the whole reason this lives in its own class.
"""

from __future__ import annotations

from idms_db2_phase2.composers.output_write.output_write_eligibility import (
    ExtractionPlan,
)
from idms_db2_phase2.composers.output_write.output_write_line_utils import (
    OutputWriteLineUtils,
)
from idms_db2_phase2.composers.output_write.output_write_renderer import (
    OutputWriteRenderer,
)
from idms_db2_phase2.composers.output_write.output_write_scanner import (
    OutputWriteScanner,
)


class OutputWriteExtractor:
    """Splices the call site in and the new paragraph after."""

    def __init__(
        self,
        line_utils: OutputWriteLineUtils | None = None,
        renderer: OutputWriteRenderer | None = None,
        scanner: OutputWriteScanner | None = None,
    ) -> None:
        self.lines = line_utils or OutputWriteLineUtils()
        self.renderer = renderer or OutputWriteRenderer(self.lines)
        self.scanner = scanner or OutputWriteScanner(self.lines)

    # ----------------------------------------------------------- public
    def apply(self, lines: list[str], plan: ExtractionPlan) -> None:
        """Rewrite `lines` in place for one accepted plan."""
        block = plan.block
        template = self.lines.template_line(lines, block.if_index)

        call_site = self.renderer.call_site_lines(
            template=template,
            indent=self.lines.call_indent(lines, block.body_start),
            paragraph=plan.paragraph,
        )
        paragraph_block = self.renderer.paragraph_lines(
            template=template,
            paragraph=plan.paragraph,
            body=plan.body,
        )

        # 1. Replace the guarded body with the PERFORM call site.
        lines[block.body_start:block.end_index] = call_site

        # 2. Insert the new paragraph after the host paragraph ends,
        #    correcting for the size change step 1 just made.
        insert_at = self._insert_index(
            lines=lines,
            end_index=block.end_index,
            shift=len(call_site) - len(plan.body),
        )
        lines[insert_at:insert_at] = paragraph_block

    # ---------------------------------------------------------- helpers
    def _insert_index(
        self,
        *,
        lines: list[str],
        end_index: int,
        shift: int,
    ) -> int:
        """Index just past the paragraph that held the extracted block."""
        return self.scanner.paragraph_end_index(lines, end_index + shift)


__all__ = ["OutputWriteExtractor"]