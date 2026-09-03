from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.idms_patterns import (
    DB_END_OF_SET_TOKEN_PATTERN,
    DB_REC_NOT_FOUND_TOKEN_PATTERN,
    IDMS_DECLARATIVE_OR_CONTROL_PATTERNS,
)
from rules.conversion_rules import (
    COMMENTED_IDMS_LINE_PREFIX,
    UNMAPPED_RECORD_MARKER_TEMPLATE,
)
from rules.idms_transformer_rules import (
    CONTINUE_STATEMENT,
    PROCEDURE_DIVISION_NAME,
    SQLCODE_END_TOKEN_REPLACEMENT,
)


class TransformerSharedMixin:
    """Shared helpers used by control/data statement converters.

    Owns the single, correct unmapped-record handling (Option B) with
    record-level tracking, and the generic token-replacement helpers.
    """

    def _keep_and_comment_unmapped(
        self,
        record: str,
        stripped_line: str,
    ) -> list[str]:
        """Register the record as unmapped and comment the verb line.

        Record-level Option B: the record is added to ``unmapped_records``
        so a downstream composer can comment EVERY line touching this
        record (not only this single IDMS verb line).
        """
        cobol_record = NameNormalizer.to_cobol(record)
        self.unmapped_records.add(cobol_record)
        return [
            UNMAPPED_RECORD_MARKER_TEMPLATE.format(record=cobol_record),
            f"{COMMENTED_IDMS_LINE_PREFIX} {stripped_line}",
        ]

    def _removed_idms_executable_lines(
        self,
        message: str,
        current_division: str,
    ) -> list[str]:
        if current_division == PROCEDURE_DIVISION_NAME:
            return [message, CONTINUE_STATEMENT]
        return [message]

    def _replace_idms_condition_tokens(
        self,
        line: str,
    ) -> list[str]:
        updated = DB_REC_NOT_FOUND_TOKEN_PATTERN.sub(
            SQLCODE_END_TOKEN_REPLACEMENT, line
        )
        updated = DB_END_OF_SET_TOKEN_PATTERN.sub(
            SQLCODE_END_TOKEN_REPLACEMENT, updated
        )
        return [updated]

    def _is_idms_declarative_or_control_statement(
        self,
        upper: str,
    ) -> bool:
        return any(
            pattern.search(upper)
            for pattern in IDMS_DECLARATIVE_OR_CONTROL_PATTERNS
        )