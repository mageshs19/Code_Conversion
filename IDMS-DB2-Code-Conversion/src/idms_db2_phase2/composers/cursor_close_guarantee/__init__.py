# LOCATION: src/idms_db2_phase2/composers/cursor_close_guarantee/__init__.py
# ACTION: CREATE NEW FILE

"""Helpers for the cursor close-guarantee pass.

CursorCloseGuaranteeComposer decides WHICH repair path a cursor needs.
This package owns everything else.

    models.py                 value objects, no logic
    message_log.py            one shared diagnostic collector
    line_utils.py             logical line read / write, condition helpers
    paragraph_index.py        paragraph discovery and navigation
    cursor_scanner.py         generated cursor paragraphs and PERFORMs
    loop_finder.py            business driving-loop discovery
    condition_normaliser.py   legacy exit test -> cursor EOC flag
    close_guarantor.py        inserts the missing PERFORM <close>
    loop_synthesiser.py       builds the manual loop shape from scratch

Import order below is dependency order, so a circular import would fail
loudly here rather than intermittently at call time.
"""

from idms_db2_phase2.composers.cursor_close_guarantee.models import (
    UNTIL_KEYWORD,
    CursorParagraphSet,
    CursorPerform,
    LoopShape,
    ParagraphHeader,
)
from idms_db2_phase2.composers.cursor_close_guarantee.message_log import (
    MessageLog,
)
from idms_db2_phase2.composers.cursor_close_guarantee.line_utils import (
    COMMENT_INDICATORS,
    CursorGuaranteeLineUtils,
)
from idms_db2_phase2.composers.cursor_close_guarantee.paragraph_index import (
    ParagraphIndex,
)
from idms_db2_phase2.composers.cursor_close_guarantee.cursor_scanner import (
    PARAGRAPH_NAME_TEMPLATE,
    CursorScanner,
)
from idms_db2_phase2.composers.cursor_close_guarantee.loop_finder import (
    BusinessLoopFinder,
)
from idms_db2_phase2.composers.cursor_close_guarantee.condition_normaliser import (
    ConditionNormaliser,
)
from idms_db2_phase2.composers.cursor_close_guarantee.close_guarantor import (
    CloseGuarantor,
)
from idms_db2_phase2.composers.cursor_close_guarantee.loop_synthesiser import (
    LoopSynthesiser,
)

__all__ = [
    # constants
    "COMMENT_INDICATORS",
    "PARAGRAPH_NAME_TEMPLATE",
    "UNTIL_KEYWORD",
    # models
    "CursorParagraphSet",
    "CursorPerform",
    "LoopShape",
    "ParagraphHeader",
    # services
    "BusinessLoopFinder",
    "CloseGuarantor",
    "ConditionNormaliser",
    "CursorGuaranteeLineUtils",
    "CursorScanner",
    "LoopSynthesiser",
    "MessageLog",
    "ParagraphIndex",
]