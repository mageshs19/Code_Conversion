"""
Backward-compatible wrapper for update COBOL final cleanup.

The professional implementation lives in:
idms_db2_phase2.services.update_cobol_final_cleanup_service

Keep this wrapper because existing composers may still import
UpdateFinalFeedbackService from this module.
"""

from __future__ import annotations

from idms_db2_phase2.services.update_cobol_final_cleanup_service import (
    UpdateCobolFinalCleanupService,
)


class UpdateFinalFeedbackService(UpdateCobolFinalCleanupService):
    """
    Backward-compatible alias for UpdateCobolFinalCleanupService.
    """

    pass


__all__ = [
    "UpdateFinalFeedbackService",
]