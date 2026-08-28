"""
DB2 date comparison composer.

This composer realigns DB2 date host fields before comparing them with
numeric COBOL date fields such as PARMDATE.

It also ensures shared DB2 date helper Working-Storage is declared when
generated update or retrieval logic uses shared date helper fields such as:

- DA-CCYYMMDD
- DA-CCYYMMDD-R
- DA-DD-MM-CCYY

No program name is hardcoded.
No table name is hardcoded.
No DCLGEN group name is hardcoded.
No business field name is hardcoded.

This class owns no regex, constants, or templates. It only orchestrates its
helper classes:
- Db2DateFieldDetector          (detection)
- Db2DateWorkingStorageManager  (Working-Storage insertion)
- Db2DateComparisonRewriter     (IF comparison rewriting)
"""

from idms_db2_phase2.composers.db2_date_comparison_rewriter import (
    Db2DateComparisonRewriter,
)
from idms_db2_phase2.composers.db2_date_field_detector import (
    Db2DateFieldDetector,
)
from idms_db2_phase2.composers.db2_date_line_utils import Db2DateLineUtils
from idms_db2_phase2.composers.db2_date_working_storage_manager import (
    Db2DateWorkingStorageManager,
)
from rules.db2_date_conversion_rules import DB2_DATE_COMPARISON_WS_MARKER


class Db2DateComparisonComposer:
    WS_MARKER = DB2_DATE_COMPARISON_WS_MARKER

    def __init__(self) -> None:
        self.line_utils = Db2DateLineUtils()
        self.field_detector = Db2DateFieldDetector(
            line_utils=self.line_utils,
        )
        self.working_storage_manager = Db2DateWorkingStorageManager(
            line_utils=self.line_utils,
        )
        self.comparison_rewriter = Db2DateComparisonRewriter(
            line_utils=self.line_utils,
        )

    def compose(self, text: str) -> str:
        if not text:
            return ""

        lines = self.line_utils.normalize_line_endings(text).splitlines()

        date_fields = self.field_detector.date_fields_used_in_comparisons(
            lines
        )
        shared_helpers_used = (
            self.field_detector.shared_date_helpers_used_in_procedure(lines)
        )

        if date_fields or shared_helpers_used:
            lines = self.working_storage_manager.ensure_date_working_storage(
                lines=lines,
                date_fields=date_fields,
            )

        if date_fields:
            lines = self.comparison_rewriter.rewrite_date_comparisons(lines)

        return "\n".join(lines).rstrip() + "\n"