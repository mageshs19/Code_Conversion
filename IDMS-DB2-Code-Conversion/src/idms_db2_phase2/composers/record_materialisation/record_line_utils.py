# LOCATION: src/idms_db2_phase2/composers/record_materialisation/record_line_utils.py
# ACTION: CREATE NEW FILE
"""Fixed-format line helpers for record materialisation.

Owns no regex and no business rules. Every method is total: a line the
service cannot parse is returned as-is rather than raising, so a single
odd line can never abort the pass.
"""

from __future__ import annotations

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)

COMMENT_INDICATOR = "*"
BLANK_INDICATOR = " "


class RecordLineUtils:
    """Reads and writes fixed-format COBOL lines."""

    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.fixed_format = fixed_format or FixedFormatLineService()

    # ------------------------------------------------------------ read
    def logical(self, line: str) -> str:
        """Columns 8-72, stripped."""
        try:
            return str(self.fixed_format.logical(line) or "").strip()
        except Exception:  # noqa: BLE001
            return str(line or "").strip()

    def body_indent(self, line: str) -> str:
        """Leading spaces of the body, as a string."""
        try:
            return str(self.fixed_format.body_indent(line) or "")
        except Exception:  # noqa: BLE001
            return ""

    def is_skippable(self, line: str) -> bool:
        """Comment / page-eject / debug / continuation, read from col 7."""
        try:
            return bool(self.fixed_format.is_comment_or_control_line(line))
        except Exception:  # noqa: BLE001
            return str(line or "").lstrip().startswith(("*", "/"))

    @staticmethod
    def level_of(body: str) -> int:
        """Level number of a data description entry, or 0."""
        parts = str(body or "").strip().split()
        if parts and parts[0].isdigit():
            return int(parts[0])
        return 0

    # ----------------------------------------------------------- write
    def emit(
        self,
        template: str,
        body: str,
        indicator: str = BLANK_INDICATOR,
    ) -> list[str]:
        """Render one logical body as one or more fixed-format lines.

        The template supplies the sequence areas, so a generated line
        carries a real sequence number instead of a placeholder.
        """
        text = str(body or "").rstrip()
        if not text:
            return []

        try:
            left, template_indicator, _old, right = self.fixed_format.split(
                template
            )
        except Exception:  # noqa: BLE001
            return [text]

        marker = (
            str(indicator or "")
            or str(template_indicator or "")
            or BLANK_INDICATOR
        )[:1]

        emitter = getattr(self.fixed_format, "emit", None)
        if callable(emitter):
            try:
                return list(emitter(left, marker, text, right))
            except Exception:  # noqa: BLE001
                pass

        try:
            built = self.fixed_format.build_or_none(
                left, marker, text, right
            )
        except Exception:  # noqa: BLE001
            built = None

        return [built] if built else [text]

    def emit_generated(self, template: str, text: str) -> list[str]:
        """Emit a generated body, routing a leading '*' to column 7."""
        stripped = str(text or "").lstrip()
        if stripped.startswith(COMMENT_INDICATOR):
            return self.emit(
                template,
                stripped.lstrip(COMMENT_INDICATOR),
                COMMENT_INDICATOR,
            )
        return self.emit(template, text, BLANK_INDICATOR)


__all__ = ["RecordLineUtils"]