# LOCATION: src/idms_db2_phase2/composers/output_write/__init__.py
# ACTION: REPLACE ENTIRE FILE
"""Output write paragraph extraction.

    output_write_line_utils.py     line inspection and cloning
    output_write_scanner.py        divisions, IF/END-IF, WRITE, paragraphs
    output_write_guard.py          structural safety gate
    output_write_block_finder.py   candidate discovery
    output_write_eligibility.py    accept / refuse decisions
    output_write_renderer.py       call site and paragraph rendering
    output_write_extractor.py      line replacement

Import order matters: every module below imports its collaborators from
the CONCRETE module path, never from this package, so nothing here can
create a cycle.
"""

from idms_db2_phase2.composers.output_write.output_write_line_utils import (
    OutputWriteLineUtils,
)
from idms_db2_phase2.composers.output_write.output_write_scanner import (
    OutputWriteScanner,
)
from idms_db2_phase2.composers.output_write.output_write_guard import (
    OutputWriteGuard,
)
from idms_db2_phase2.composers.output_write.output_write_renderer import (
    OutputWriteRenderer,
)
from idms_db2_phase2.composers.output_write.output_write_block_finder import (
    UNNAMED_PARAGRAPH,
    CandidateBlock,
    OutputWriteBlockFinder,
)
from idms_db2_phase2.composers.output_write.output_write_eligibility import (
    ExtractionPlan,
    OutputWriteEligibility,
    Refusal,
)
from idms_db2_phase2.composers.output_write.output_write_extractor import (
    OutputWriteExtractor,
)

__all__ = [
    "UNNAMED_PARAGRAPH",
    "CandidateBlock",
    "ExtractionPlan",
    "OutputWriteBlockFinder",
    "OutputWriteEligibility",
    "OutputWriteExtractor",
    "OutputWriteGuard",
    "OutputWriteLineUtils",
    "OutputWriteRenderer",
    "OutputWriteScanner",
    "Refusal",
]