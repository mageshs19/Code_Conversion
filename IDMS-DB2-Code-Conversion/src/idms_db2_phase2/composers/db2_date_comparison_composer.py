# LOCATION: src/idms_db2_phase2/composers/db2_date_comparison_composer.py
# ACTION: REPLACE ENTIRE FILE

"""DB2 date comparison composer.

Realigns DB2 date host fields before they are compared with a numeric
COBOL date field, and declares the shared date helper Working-Storage
(DA-CCYYMMDD, DA-CCYYMMDD-R, DA-DD-MM-CCYY) plus one HELP- field per
converted host.

No program, table, DCLGEN group or business field name is hardcoded.

This class owns no regex, constants or templates. It only orchestrates:

    Db2DateConditionAssembler     joins one IF across physical lines
    Db2DateFieldDetector          finds DATE operands in a condition
    Db2DateWorkingStorageManager  declares the helper fields
    Db2DateComparisonRewriter     emits realignment + rewrites the IF

CORRECTION 1 - the pass was silent when it did nothing
-------------------------------------------------------
compose() returned the text unchanged and exposed no `messages`, so a
program whose date comparison could not be detected looked exactly like
a program with no dates at all. VMDZ7200 shipped comparing a 10-byte
DD.MM.CCYY host against an 8-byte CCYYMMDD field and nothing in the
conversion log said so. `messages` is now populated on EVERY path,
including the no-op path, and conversion_service._component_messages
picks it up automatically.

CORRECTION 2 - detection could not see the real condition
----------------------------------------------------------
The detector matched one physical line against a pattern that required
the DATE host to be the first token after IF AND required the literal
token PARMDATE. Both constraints are gone; see
patterns/db2_date_patterns.py.

ORDERING
--------
Working-Storage is ensured BEFORE the rewrite. The rewrite inserts lines
into the PROCEDURE DIVISION and re-scans from scratch, so the earlier
DATA DIVISION insertion cannot invalidate its indexes.
"""

from __future__ import annotations

from idms_db2_phase2.composers.db2_date_comparison_rewriter import (
    Db2DateComparisonRewriter,
)
from idms_db2_phase2.composers.db2_date_condition_assembler import (
    Db2DateConditionAssembler,
)
from idms_db2_phase2.composers.db2_date_field_detector import (
    Db2DateFieldDetector,
)
from idms_db2_phase2.composers.db2_date_line_utils import Db2DateLineUtils
from idms_db2_phase2.composers.db2_date_working_storage_manager import (
    Db2DateWorkingStorageManager,
)
from rules.db2_date_conversion_rules import (
    DB2_DATE_COMPARISON_WS_MARKER,
    DB2_DATE_MESSAGES,
    ENFORCE_DATE_COMPARISON_CONVERSION,
)


class Db2DateComparisonComposer:
    """Declares date helpers and converts every DATE host comparison."""

    WS_MARKER = DB2_DATE_COMPARISON_WS_MARKER

    def __init__(self) -> None:
        self.line_utils = Db2DateLineUtils()

        self.condition_assembler = Db2DateConditionAssembler(
            line_utils=self.line_utils,
        )
        self.field_detector = Db2DateFieldDetector(
            line_utils=self.line_utils,
            assembler=self.condition_assembler,
        )
        self.working_storage_manager = Db2DateWorkingStorageManager(
            line_utils=self.line_utils,
        )
        self.comparison_rewriter = Db2DateComparisonRewriter(
            line_utils=self.line_utils,
            assembler=self.condition_assembler,
            detector=self.field_detector,
        )

        self.messages: list[str] = []

    #
    # Public entry point
    #
    def compose(self, text: str) -> str:
        self.messages = []

        if not text:
            return ""

        if not ENFORCE_DATE_COMPARISON_CONVERSION:
            return str(text)

        lines = self.line_utils.normalize_line_endings(text).splitlines()

        if not lines:
            return ""

        date_fields = self.field_detector.date_fields_used_in_comparisons(
            lines
        )
        shared_helpers_used = (
            self.field_detector.shared_date_helpers_used_in_procedure(lines)
        )

        #
        # Nothing to do. Say so, rather than returning in silence.
        #
        if not date_fields and not shared_helpers_used:
            self.messages.append(DB2_DATE_MESSAGES["nothing_found"])
            return "\n".join(lines).rstrip() + "\n"

        #
        # 1. Working-Storage.
        #
        if date_fields or shared_helpers_used:
            lines = self.working_storage_manager.ensure_date_working_storage(
                lines,
                date_fields,
            )

            if date_fields:
                self.messages.append(
                    DB2_DATE_MESSAGES["helpers_declared"].format(
                        count=len(date_fields),
                    )
                )

        #
        # 2. Realignment and condition rewrite.
        #
        if date_fields:
            lines = self.comparison_rewriter.rewrite_date_comparisons(lines)
            self.messages.extend(self._rewriter_messages())

        return "\n".join(lines).rstrip() + "\n"

    #
    # Helpers
    #
    def _rewriter_messages(self) -> list[str]:
        """Drain the rewriter's diagnostics, blank entries removed."""
        raw = getattr(self.comparison_rewriter, "messages", None) or []

        return [
            str(message)
            for message in raw
            if str(message or "").strip()
        ]


__all__ = ["Db2DateComparisonComposer"]