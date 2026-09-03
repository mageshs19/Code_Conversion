from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.field_reference_rewriter_patterns import (
    GENERATED_OBTAIN_COMMENT_PATTERN,
    INITIALIZE_DCL_PATTERN,
    MOVE_SPACES_TO_RECORD_PATTERN,
    PARAGRAPH_PATTERN,
    QUALIFIED_REFERENCE_PATTERN,
)


class FieldReferenceRecordContext:
    """
    Detects active record context for safe bare field rewriting.
    """

    def __init__(
        self,
        *,
        record_field_map: dict[str, dict[str, str]],
        group_record_map: dict[str, str],
    ) -> None:
        self.record_field_map = record_field_map
        self.group_record_map = group_record_map

    def detect_active_record_from_line(
        self,
        *,
        logical_line: str,
        current_active_record: str,
    ) -> str:
        logical = str(logical_line or "").strip()

        if not logical:
            return current_active_record

        for detector in [
            self.record_from_paragraph,
            self.record_from_initialize,
            self.record_from_generated_comment,
            self.record_from_move_target,
            self.record_from_qualified_reference,
        ]:
            record = detector(logical)

            if record:
                return record

        return current_active_record

    def record_from_paragraph(
        self,
        logical_line: str,
    ) -> str:
        match = PARAGRAPH_PATTERN.match(logical_line)

        if not match:
            return ""

        paragraph = NameNormalizer.normalize(match.group("name"))

        for record in self.record_field_map:
            if record and record in paragraph:
                return record

        return ""

    def record_from_initialize(
        self,
        logical_line: str,
    ) -> str:
        match = INITIALIZE_DCL_PATTERN.search(logical_line)

        if not match:
            return ""

        group = NameNormalizer.normalize(match.group("group"))

        return self.group_record_map.get(group, "")

    def record_from_generated_comment(
        self,
        logical_line: str,
    ) -> str:
        match = GENERATED_OBTAIN_COMMENT_PATTERN.search(logical_line)

        if not match:
            return ""

        record = NameNormalizer.normalize(match.group("record"))

        if record in self.record_field_map:
            return record

        return ""

    def record_from_move_target(
        self,
        logical_line: str,
    ) -> str:
        match = MOVE_SPACES_TO_RECORD_PATTERN.search(logical_line)

        if not match:
            return ""

        record = NameNormalizer.normalize(match.group("record"))

        if record in self.record_field_map:
            return record

        return ""

    def record_from_qualified_reference(
        self,
        logical_line: str,
    ) -> str:
        match = QUALIFIED_REFERENCE_PATTERN.search(logical_line)

        if not match:
            return ""

        record = NameNormalizer.normalize(match.group("record"))

        if record in self.record_field_map:
            return record

        return ""