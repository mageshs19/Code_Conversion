from __future__ import annotations

from idms_db2_phase2.postprocess.final_cleanup.final_cleanup_dcl_reference import (
    FinalCleanupDclReference,
)
from idms_db2_phase2.postprocess.final_cleanup.final_cleanup_line_utils import (
    FinalCleanupLineUtils,
)
from idms_db2_phase2.postprocess.final_cleanup.final_cleanup_normalizer import (
    FinalCleanupNormalizer,
)
from patterns.update_final_cleanup_patterns import (
    CONVERTED_MODIFY_COMMENT_PATTERN,
    DCL_REFERENCE_PATTERN,
    INITIALIZE_DCL_PATTERN,
    MOVE_SPACES_TO_BARE_RECORD_PATTERN,
)
from rules.update_cobol_final_cleanup_rules import (
    FINAL_CLEANUP_MAX_CONSECUTIVE_BLANKS,
)


class UpdateFinalCleanup(
    FinalCleanupLineUtils,
    FinalCleanupDclReference,
    FinalCleanupNormalizer,
):
    """Final update-only cleanup after fixed-format resequencing.

    Orchestration only. Fixed-format helpers, DCL reference rewriting, and
    paragraph/procedure normalization are provided by mixins. All COBOL tokens
    and column geometry live in rules/update_cobol_final_cleanup_rules.py.

    Narrow, generic fixes only; does not rename variables/paragraphs and does
    not touch retrieval.
    """

    def apply(self, text: str) -> str:
        if not text:
            return ""

        lines = (
            str(text or "")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .splitlines()
        )

        lines = self._remove_leftover_modify_comments(lines)
        lines = self._rewrite_non_sql_dcl_dot_references(lines)
        lines = self._remove_obsolete_bare_record_initializes(lines)
        lines = self._normalize_update_paragraphs(lines)
        lines = self._normalize_procedure_simple_blocks(lines)
        lines = self._normalize_excess_blank_lines(lines)

        return "\n".join(lines).rstrip() + "\n"

    def _remove_leftover_modify_comments(self, lines: list[str]) -> list[str]:
        output: list[str] = []
        for line in lines:
            logical = self._body(line).strip()
            raw = str(line or "")
            if CONVERTED_MODIFY_COMMENT_PATTERN.search(logical):
                continue
            if CONVERTED_MODIFY_COMMENT_PATTERN.search(raw):
                continue
            output.append(line)
        return output

    def _remove_obsolete_bare_record_initializes(
        self, lines: list[str]
    ) -> list[str]:
        remove_indexes: set[int] = set()

        for start, end in self._paragraph_ranges(lines):
            paragraph = lines[start:end]

            has_dcl_initialize = any(
                INITIALIZE_DCL_PATTERN.match(self._logical(line))
                for line in paragraph
            )
            has_dcl_usage = any(
                DCL_REFERENCE_PATTERN.search(self._logical(line))
                for line in paragraph
            )
            if not has_dcl_initialize or not has_dcl_usage:
                continue

            for index in range(start + 1, end):
                if MOVE_SPACES_TO_BARE_RECORD_PATTERN.match(self._logical(lines[index])):
                    remove_indexes.add(index)

        if not remove_indexes:
            return lines

        return [
            line for index, line in enumerate(lines) if index not in remove_indexes
        ]

    def _normalize_excess_blank_lines(self, lines: list[str]) -> list[str]:
        output: list[str] = []
        blank_count = 0

        for line in lines:
            if self._logical(line):
                blank_count = 0
                output.append(line)
                continue

            blank_count += 1
            if blank_count <= FINAL_CLEANUP_MAX_CONSECUTIVE_BLANKS:
                output.append(line)

        return output