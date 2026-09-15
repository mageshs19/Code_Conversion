# LOCATION: src/idms_db2_phase2/postprocess/update_storage_include_manager.py
# ACTION: REPLACE ENTIRE FILE

from __future__ import annotations

import re

from idms_db2_phase2.generators.sql_error_generator import SqlErrorGenerator
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
    MSG_SQLERROR_FROM_COPYBOOK,
    MSG_SQLERROR_INJECTED,
    SQL_ERROR_INCLUDE_TOKEN,
    SQLERROR_PARAGRAPH_TEMPLATE,
    USE_SHARED_SQL_ERROR_GENERATOR,
)

# ---------------------------------------------------------------------------
# Self-contained legacy abend-marker patterns.
#
# CORRECTION - two of these patterns could never match.
#
# They previously read:
#
#     PIC\s+X$\d+$
#
# '$' is the END-OF-STRING ANCHOR, not a literal parenthesis. "X$\d+$"
# means "literal X, then end of string, then digits, then end of string",
# which is unsatisfiable. The intended expression is "X$\d+$", i.e.
# PIC X(08).
#
# The corruption came from a PDF/OCR round trip, and the comment that
# claimed "with correct $\d+$ escaping" carried it forward. Cases (b),
# (d) and (e) in remove_legacy_restart_working_storage therefore never
# fired, and legacy abend markers were silently left in the output.
#
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

# SQLERROR detection, matched against the whole program text.
_PERFORM_SQLERROR = re.compile(
    r"\bPERFORM\s+SQLERROR\b",
    flags=re.IGNORECASE,
)
_SQLERROR_HEADER = re.compile(
    r"^\s*(?:\d{6}\s*)?SQLERROR\s*\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

# Fixed-format geometry, used by the self-contained _logical helper.
_LEFT_SEQUENCE_WIDTH = 6
_RIGHT_SEQUENCE_START = 72
_RIGHT_SEQUENCE_END = 80
_FIXED_LINE_WIDTH = 80


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
        """Strip the fixed-format sequence areas, then strip whitespace.

        CORRECTION - the right-sequence test was content-based.

        It read:

            if len(text) >= 8 and text[-8:].strip().isdigit():

        which removes the last eight characters of ANY line ending in
        eight digits, including a genuine statement such as

            MOVE 12345678 TO WS-FIELD

        The test is now COLUMN-based: columns 73-80 are only treated as a
        right sequence on a line that is actually 80 columns wide.
        """
        text = str(line or "").rstrip("\n")

        if (
            len(text) >= _FIXED_LINE_WIDTH
            and text[_RIGHT_SEQUENCE_START:_RIGHT_SEQUENCE_END].isdigit()
        ):
            text = text[:_RIGHT_SEQUENCE_START]

        if (
            len(text) >= _LEFT_SEQUENCE_WIDTH
            and text[:_LEFT_SEQUENCE_WIDTH].isdigit()
        ):
            return text[_LEFT_SEQUENCE_WIDTH:].strip()

        # Free-form fallback: a leading run of six digits after indent.
        stripped = text.lstrip()
        if (
            len(stripped) >= _LEFT_SEQUENCE_WIDTH
            and stripped[:_LEFT_SEQUENCE_WIDTH].isdigit()
        ):
            return stripped[_LEFT_SEQUENCE_WIDTH:].strip()

        return text.strip()

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
                LEGACY_77_DECLARATION_PATTERN_TEMPLATE.format(
                    name=re.escape(name)
                ),
                flags=re.IGNORECASE,
            )
            for name in UPDATE_LEGACY_RESTART_WS_NAMES
        ]

        index = 0
        total = len(lines)

        while index < total:
            line = lines[index]
            logical = self._logical(line)

            # (a) legacy named 77 fields (CTR-REC, SW-EOF, SW-RECAB)
            if any(pattern.match(logical) for pattern in legacy_patterns):
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
                while look < total and not self._logical(lines[look]).strip():
                    look += 1

                if look < total and _ABEND_VALUE_LINE.match(
                    self._logical(lines[look])
                ):
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

    # ------------------------------------------------------------------
    # SQLERROR routine
    # ------------------------------------------------------------------
    def ensure_sqlerror_paragraph(self, cobol_text, diagnostics=None):
        """Append the SQLERROR routine once, if the program needs one.

        CORRECTION - this injected the WRONG body, and injected it even
        when the copybook already supplied the routine.

        The method looked only for a local 'SQLERROR.' paragraph header.
        Under the site standard there is none: the routine arrives through

            EXEC SQL
                 INCLUDE SQLERROR
            END-EXEC.

        so the header was correctly absent, and this method then appended
        the legacy DISPLAY / CALL USERABEN body on top of it. That
        duplicated the copybook routine and made the update output
        diverge from the retrieval output. CHK-05.08 reported it.

        Two changes:

          - the INCLUDE form now counts as "already present";
          - the body comes from the shared SqlErrorGenerator, so both
            program families emit one routine.
        """
        text = str(cobol_text or "")

        # Only needed if something calls PERFORM SQLERROR.
        if not _PERFORM_SQLERROR.search(text):
            return text

        # A local paragraph header already defines it.
        if _SQLERROR_HEADER.search(text):
            return text

        # The copybook already supplies it. Appending a second body here
        # is what produced the duplicate routine.
        if SQL_ERROR_INCLUDE_TOKEN.upper() in text.upper():
            if diagnostics is not None:
                diagnostics.append(MSG_SQLERROR_FROM_COPYBOOK)
            return text

        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

        # Drop trailing blank lines so the block appends cleanly.
        while lines and not lines[-1].strip():
            lines.pop()

        lines.append("")
        lines.extend(self._sql_error_lines())

        if diagnostics is not None:
            diagnostics.append(MSG_SQLERROR_INJECTED)

        return "\n".join(lines).rstrip() + "\n"

    def _sql_error_lines(self) -> list[str]:
        """The SQLERROR routine body, from the single shared generator.

        SQLERROR_PARAGRAPH_TEMPLATE is retained only as a fallback, so a
        site that has not yet adopted the copybook form can switch back
        by setting USE_SHARED_SQL_ERROR_GENERATOR to False.
        """
        if USE_SHARED_SQL_ERROR_GENERATOR:
            return list(SqlErrorGenerator().paragraph_lines())

        return list(SQLERROR_PARAGRAPH_TEMPLATE)