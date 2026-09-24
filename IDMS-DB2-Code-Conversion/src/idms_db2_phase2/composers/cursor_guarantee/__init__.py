# LOCATION: src/idms_db2_phase2/composers/cursor_guarantee/__init__.py
# ACTION: CREATE NEW FILE

"""Helpers for the cursor close-guarantee pass.

CursorCloseGuaranteeComposer decides WHICH repair path a cursor needs.
This package owns everything else:

    cursor_models.py    regex, value objects, diagnostic log
    cursor_lines.py     logical lines, paragraph navigation
    cursor_scanner.py   discovery, read-only
    cursor_repair.py    every mutation

Import order below is dependency order, so a circular import fails
loudly here rather than intermittently at call time. Nothing in this
package imports patterns/ - see the CORRECTION note in cursor_models.py.
"""

from idms_db2_phase2.composers.cursor_guarantee.cursor_models import (
    COMMENT_INDICATORS,
    PARAGRAPH_NAME_TEMPLATE,
    UNTIL_KEYWORD,
    CursorParagraphSet,
    CursorPerform,
    LoopShape,
    MessageLog,
    ParagraphHeader,
)
from idms_db2_phase2.composers.cursor_guarantee.cursor_lines import CursorLines
from idms_db2_phase2.composers.cursor_guarantee.cursor_scanner import (
    CursorScanner,
)
from idms_db2_phase2.composers.cursor_guarantee.cursor_repair import CursorRepair

__all__ = [
    "COMMENT_INDICATORS",
    "PARAGRAPH_NAME_TEMPLATE",
    "UNTIL_KEYWORD",
    "CursorParagraphSet",
    "CursorPerform",
    "LoopShape",
    "MessageLog",
    "ParagraphHeader",
    "CursorLines",
    "CursorScanner",
    "CursorRepair",
]