from __future__ import annotations

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from rules.update_cobol_final_cleanup_rules import (
    PROTECTED_BARE_TARGET_PREFIXES,
)


class UpdateCobolFinalCleanupUtils:
    """
    Shared fixed-format helper methods for update COBOL final cleanup.
    """

    def __init__(
        self,
        fixed_format: FixedFormatLineService,
    ) -> None:
        self.fixed_format = fixed_format

    def body_with_existing_indent(
        self,
        *,
        original_line: str,
        new_logical: str,
    ) -> str:
        body = self.fixed_format.body(original_line)
        leading = body[: len(body) - len(body.lstrip(" "))]

        if not leading:
            leading = "    "

        return leading + str(new_logical or "").strip()

    def comment_body_for_line(
        self,
        *,
        original_line: str,
        comment_text: str,
    ) -> str:
        """
        Return the correct body for a comment line.

        In fixed-format COBOL, the comment indicator is already in column 7.
        Therefore, if the replacement text starts with '*', remove it from
        the body to avoid producing '**DB2...' physically.
        """

        text = str(comment_text or "").strip()

        if text.startswith("*"):
            text = text[1:].lstrip()

        body = self.fixed_format.body(original_line)
        leading = body[: len(body) - len(body.lstrip(" "))]

        return leading + text

    def is_protected_bare_target(
        self,
        target: str,
    ) -> bool:
        normalized = str(target or "").upper()

        return any(
            normalized.startswith(prefix)
            for prefix in PROTECTED_BARE_TARGET_PREFIXES
        )