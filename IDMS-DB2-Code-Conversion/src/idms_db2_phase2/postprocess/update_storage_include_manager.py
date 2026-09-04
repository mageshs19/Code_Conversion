from __future__ import annotations

import re

from idms_db2_phase2.postprocess.cobol_update_standard_generator import (
    CobolUpdateStandardGenerator,
)
from idms_db2_phase2.postprocess.storage_include.storage_include_injector import (
    StorageIncludeInjector,
)
from idms_db2_phase2.postprocess.storage_include.storage_ws_injector import (
    StorageWsInjector,
)
from idms_db2_phase2.postprocess.update_postprocess_line_utils import (
    UpdatePostprocessLineUtils,
)
from patterns.update_storage_include_patterns import (
    LEGACY_77_DECLARATION_PATTERN_TEMPLATE,
)
from rules.update_restart_rules import (
    UPDATE_LEGACY_RESTART_WS_NAMES,
    UPDATE_RESTART_DIAGNOSTICS,
)
from rules.update_standard_generator_templates import (
    SQLERROR_PARAGRAPH_TEMPLATE,   # ADDED
)

# ---------------------------------------------------------------------------
# Self-contained legacy abend-marker patterns.
# Defined here inline (with correct $\d+$ escaping) so this cleanup does NOT
# depend on external pattern-file edits that may be missing or OCR-broken.
# All patterns match the SEQUENCE-STRIPPED logical line.
# ---------------------------------------------------------------------------
_ABEND_ONELINE = re.compile(
    r"^\s*77\s+[A-Z0-9-]+\s+PIC\s+X$\d+$\s+VALUE\s+'##&&[^']*'\s*\.?\s*$",
    flags=re.IGNORECASE,
)
_ABEND_VALUE_LINE = re.compile(
    r"^\s*VALUE\s+'##&&[^']*'\s*\.?\s*$",
    flags=re.IGNORECASE,
)
_ABEND_77_HEADER_NAMED = re.compile(
    r"^\s*77\s+(?P<name>[A-Z0-9-]+)\s+PIC\s+X$\d+$\s*\.?\s*$",
    flags=re.IGNORECASE,
)


class UpdateStorageIncludeManager(
    StorageWsInjector,
    StorageIncludeInjector,
):
    """Manages update-program storage and include injection.

    Orchestration + legacy WS removal live here. Working-storage/program-name
    passes and include injection are provided by mixins.
    """

    def __init__(
        self,
        *,
        generator: CobolUpdateStandardGenerator,
        line_utils: UpdatePostprocessLineUtils,
    ) -> None:
        self.generator = generator
        self.line_utils = line_utils

    # ------------------------------------------------------------------
    # Self-contained helpers (do not rely on line_utils internals).
    # ------------------------------------------------------------------
    @staticmethod
    def _logical(line: str) -> str:
        """Strip a leading 6-digit sequence and a trailing 8-digit sequence,
        then strip whitespace. Works for manual-style sequenced COBOL.
        """
        text = str(line or "").rstrip("\n")
        # drop trailing right-sequence (cols 73-80) if present
        if len(text) >= 8 and text[-8:].strip().isdigit():
            text = text[:-8]
        # drop leading left-sequence (cols 1-6) if present
        stripped = text.lstrip()
        if len(stripped) >= 6 and stripped[:6].strip().isdigit():
            stripped = stripped[6:]
        return stripped.strip()

    def _field_reference_count(self, field_name: str, cobol_text: str) -> int:
        pattern = re.compile(
            r"(?<![A-Z0-9-])" + re.escape(field_name) + r"(?![A-Z0-9-])",
            flags=re.IGNORECASE,
        )
        return len(pattern.findall(cobol_text))

    # ------------------------------------------------------------------
    # Legacy restart / abend-marker WS removal.
    # ------------------------------------------------------------------
    def remove_legacy_restart_working_storage(self, cobol_text, diagnostics):
        cobol_text = str(cobol_text or "")
        lines = cobol_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

        output: list[str] = []
        removed = False

        legacy_patterns = [
            re.compile(
                LEGACY_77_DECLARATION_PATTERN_TEMPLATE.format(name=re.escape(name)),
                flags=re.IGNORECASE,
            )
            for name in UPDATE_LEGACY_RESTART_WS_NAMES
        ]

        index = 0
        n = len(lines)
        while index < n:
            line = lines[index]
            logical = self._logical(line)

            # (a) legacy named 77 fields (CTR-REC, SW-EOF, SW-RECAB)
            if any(p.match(logical) for p in legacy_patterns):
                removed = True
                index += 1
                continue

            # (b) single-line abend marker (header + ##&& value together)
            if _ABEND_ONELINE.match(logical):
                removed = True
                index += 1
                continue

            # (c) orphaned ##&& VALUE line on its own
            if _ABEND_VALUE_LINE.match(logical):
                removed = True
                index += 1
                continue

            # (d)+(e) a "77 name PIC X(nn)" header with NO inline VALUE.
            named = _ABEND_77_HEADER_NAMED.match(logical)
            if named:
                field_name = named.group("name")

                # (d) wrapped: next non-blank logical line is a ##&& VALUE.
                look = index + 1
                while look < n and not self._logical(lines[look]).strip():
                    look += 1
                if look < n and _ABEND_VALUE_LINE.match(self._logical(lines[look])):
                    removed = True
                    index = look + 1  # drop header .. value inclusive
                    continue

                # (e) dead orphan: value already stripped in a prior run.
                #     Remove only if the field name is unused elsewhere.
                if self._field_reference_count(field_name, cobol_text) <= 1:
                    removed = True
                    index += 1
                    continue

            output.append(line)
            index += 1

        if removed and diagnostics is not None:
            diagnostics.append(UPDATE_RESTART_DIAGNOSTICS["legacy_ws_removed"])

        return "\n".join(output).rstrip() + "\n"
    
    # --- ADD this method inside class UpdateStorageIncludeManager ---
    def ensure_sqlerror_paragraph(self, cobol_text, diagnostics=None):
        """Append the SQLERROR paragraph once if the program PERFORMs it but
        never defines it. Placed after the last PROCEDURE DIVISION line.
        """
        text = str(cobol_text or "")

        # Only needed if something calls PERFORM SQLERROR.
        if not re.search(r"\bPERFORM\s+SQLERROR\b", text, re.IGNORECASE):
            return text

        # Skip if a SQLERROR paragraph header already exists.
        if re.search(r"^\s*(?:\d{6}\s*)?SQLERROR\s*\.\s*(?:\d{8})?\s*$",
                     text, re.IGNORECASE | re.MULTILINE):
            return text

        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

        # Drop a trailing blank line to append cleanly.
        while lines and not lines[-1].strip():
            lines.pop()

        # Blank spacer then the paragraph body (Area A header, Area B body).
        block = [""]
        for line in SQLERROR_PARAGRAPH_TEMPLATE:
            block.append(line)                     # header + body verbatim
        lines.extend(block)

        if diagnostics is not None:
            diagnostics.append("Injected standard SQLERROR paragraph.")

        return "\n".join(lines).rstrip() + "\n"