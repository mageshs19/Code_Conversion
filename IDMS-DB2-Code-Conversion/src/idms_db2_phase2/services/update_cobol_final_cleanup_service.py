"""
Update COBOL final cleanup service.

Generic behavior:
- Converts non-SQL DCLGEN dot references to COBOL OF qualification.
- Replaces residual bare IDMS record initialization with resolved DCLGEN
  group initialization when there is strong local DCLGEN context.
- Populates update audit host variables before UPDATE SQL blocks.
- Replaces generated DB2 diagnostic labels that still contain IDMS record names
  with nearby resolved DB2 table names.
- Does not hardcode program names, records, DB2 tables, DB2 columns,
  DCLGEN groups, or host variables.
"""

from __future__ import annotations

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from idms_db2_phase2.services.update_audit_move_inserter import (
    UpdateAuditMoveInserter,
)
from idms_db2_phase2.services.update_cobol_final_cleanup_utils import (
    UpdateCobolFinalCleanupUtils,
)
from idms_db2_phase2.services.update_cobol_reference_cleanup import (
    UpdateCobolReferenceCleanup,
)
from idms_db2_phase2.services.update_diagnostic_label_normalizer import (
    UpdateDiagnosticLabelNormalizer,
)


class UpdateCobolFinalCleanupService:
    """
    Public service for generic update-program final cleanup.

    This class only orchestrates focused cleanup helpers.
    """

    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.fixed_format = fixed_format or FixedFormatLineService()
        self.utils = UpdateCobolFinalCleanupUtils(self.fixed_format)

        self.reference_cleanup = UpdateCobolReferenceCleanup(
            fixed_format=self.fixed_format,
            utils=self.utils,
        )
        self.audit_move_inserter = UpdateAuditMoveInserter(
            fixed_format=self.fixed_format,
            utils=self.utils,
        )
        self.diagnostic_label_normalizer = UpdateDiagnosticLabelNormalizer(
            fixed_format=self.fixed_format,
            utils=self.utils,
        )

    def apply(
        self,
        text: str,
    ) -> str:
        output = str(text or "")

        if not output:
            return ""

        output = self.reference_cleanup.normalize_non_sql_dcl_dot_references(output)
        output = self.reference_cleanup.replace_bare_record_initialization(output)
        output = self.audit_move_inserter.insert_update_audit_moves(output)
        output = self.diagnostic_label_normalizer.normalize_db2_diagnostic_labels(
            output
        )

        return output.rstrip() + "\n"