# LOCATION: src/idms_db2_phase2/testing/execution/output_reader.py
# ACTION: CREATE NEW FILE

"""Reads meaning out of a runner's console output.

The batch launches each runner as a subprocess, so its output IS the
contract. This module turns that text into a status, a one-line note,
metadata counts, and a short failure explanation.

CORRECTION - failure detail showed INFO lines
---------------------------------------------
The first version printed the last five stderr lines. LoggerFactory
attaches a StreamHandler, which defaults to stderr, so a rejected review
reported five INFO lines about copybook parsing instead of the blocking
check id. Detail is now assembled in priority order and INFO and DEBUG
are excluded outright.
"""

from __future__ import annotations

from patterns.batch_console_patterns import (
    BLOCKING_PATTERN,
    CONVERSION_FAILED_PATTERN,
    COPYBOOK_FIELDS_PATTERN,
    DCLGEN_COLUMNS_PATTERN,
    ERROR_LINE_PATTERN,
    LOG_LINE_PATTERN,
    MAPPING_ROWS_PATTERN,
    NOTHING_TO_DO_PATTERN,
    QUIET_VERDICT_PATTERN,
    REPORT_FOLDER_PATTERN,
    REVIEW_SUMMARY_PATTERN,
    TRACEBACK_PATTERN,
)
from rules.batch_console_rules import (
    CONVERT_EXIT_STATUS,
    DETAIL_LOG_LEVELS,
    DETAIL_MAX_LINES,
    MSG_BLOCKING_TEMPLATE,
    MSG_VERDICT_TEMPLATE,
    REVIEW_EXIT_STATUS,
    REVIEW_NOTE_TEMPLATE,
    STATUS_FAILED,
    STATUS_NOTHING,
    VALUE_UNKNOWN,
)


class OutputReader:
    """Interprets runner stdout and stderr."""

    # =================================================================
    # Status
    # =================================================================
    @staticmethod
    def status_for(code: int, stdout: str, is_review: bool) -> str:
        """Map an exit code to a status, honouring 'nothing to do'.

        A runner that finds no programs exits 2, the same code it uses
        for a genuine error. Its own wording disambiguates, so an empty
        program folder reports NOTHING rather than a false failure.
        """
        if NOTHING_TO_DO_PATTERN.search(stdout or ""):
            return STATUS_NOTHING

        table = REVIEW_EXIT_STATUS if is_review else CONVERT_EXIT_STATUS
        return table.get(code, STATUS_FAILED)

    @staticmethod
    def note_for(stdout: str, is_review: bool) -> str:
        """The one-line summary shown beside a completed step."""
        if not is_review:
            return ""

        match = REVIEW_SUMMARY_PATTERN.search(stdout or "")
        if not match:
            return ""

        return REVIEW_NOTE_TEMPLATE.format(
            reviewed=match.group("reviewed"),
            accepted=match.group("accepted"),
            rejected=match.group("rejected"),
        )

    # =================================================================
    # Metadata
    # =================================================================
    @classmethod
    def mapping_rows(cls, text: str) -> str:
        return cls._first(MAPPING_ROWS_PATTERN, text, "count")

    @classmethod
    def dclgen_columns(cls, text: str) -> str:
        return cls._first(DCLGEN_COLUMNS_PATTERN, text, "count")

    @classmethod
    def copybook_fields(cls, text: str) -> str:
        return cls._first(COPYBOOK_FIELDS_PATTERN, text, "count")

    @classmethod
    def report_folder(cls, text: str) -> str:
        value = cls._first(REPORT_FOLDER_PATTERN, text, "path")
        return "" if value == VALUE_UNKNOWN else value

    @staticmethod
    def _first(pattern, text: str, group: str) -> str:
        match = pattern.search(text or "")
        if not match:
            return VALUE_UNKNOWN
        return str(match.group(group)).strip() or VALUE_UNKNOWN

    # =================================================================
    # Failure detail
    # =================================================================
    @staticmethod
    def failure_lines(combined: str) -> list[str]:
        """The few facts that explain a failure.

        Priority order:
          1. blocking check ids from a rejected code review
          2. the per-program verdict lines
          3. explicit ERROR: lines
          4. a conversion-failed list
          5. WARNING and above from the logger stream
          6. exception lines from a traceback

        INFO and DEBUG are deliberately excluded: they belong in the log
        file, not in a summary read at a glance.
        """
        text = combined or ""
        out: list[str] = []
        seen: set[str] = set()

        def add(value: str) -> None:
            clean = " ".join(str(value or "").split())
            if clean and clean not in seen:
                seen.add(clean)
                out.append(clean)

        for match in BLOCKING_PATTERN.finditer(text):
            add(MSG_BLOCKING_TEMPLATE.format(ids=match.group("ids").strip()))

        for match in QUIET_VERDICT_PATTERN.finditer(text):
            add(
                MSG_VERDICT_TEMPLATE.format(
                    verdict=match.group("verdict").upper(),
                    name=match.group("name"),
                )
            )

        for match in ERROR_LINE_PATTERN.finditer(text):
            add(match.group("message"))

        for match in CONVERSION_FAILED_PATTERN.finditer(text):
            add(f"Conversion failed: {match.group('names')}")

        for raw in text.splitlines():
            match = LOG_LINE_PATTERN.match(raw.strip())
            if match and match.group("level").upper() in DETAIL_LOG_LEVELS:
                add(match.group("message"))

        for match in TRACEBACK_PATTERN.finditer(text):
            add(match.group("line"))

        return out[:DETAIL_MAX_LINES]