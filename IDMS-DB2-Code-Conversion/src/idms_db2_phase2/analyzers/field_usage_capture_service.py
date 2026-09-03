from __future__ import annotations

from idms_db2_phase2.analyzers.field_usage_models import (
    FieldUsage,
    FieldUsageAnalysis,
)
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.field_usage_analysis_patterns import (
    DCLGEN_DOT_PATTERN,
    DCLGEN_OF_PATTERN,
    MOVE_PATTERN,
    QUALIFIED_REFERENCE_PATTERN,
)
from rules.field_usage_rules import (
    DCLGEN_GROUP_PREFIX,
    OUTPUT_TARGET_PREFIXES,
)


class FieldUsageCaptureService:
    """
    Captures field usage from individual COBOL logical statements.

    This service does not manage Procedure Division state. It only receives a
    logical line and updates FieldUsageAnalysis.
    """

    def __init__(
        self,
        *,
        mapping_records: set[str],
        group_to_record: dict[str, str],
    ) -> None:
        self.mapping_records = mapping_records
        self.group_to_record = group_to_record

    def capture_idms_qualified_references(
        self,
        *,
        logical: str,
        result: FieldUsageAnalysis,
        is_condition: bool,
    ) -> None:
        for match in QUALIFIED_REFERENCE_PATTERN.finditer(logical):
            field_name = NameNormalizer.to_cobol(match.group("field"))
            record_name = NameNormalizer.normalize(match.group("record"))

            if not field_name or not record_name:
                continue

            if record_name.startswith(DCLGEN_GROUP_PREFIX):
                continue

            if record_name not in self.mapping_records:
                continue

            usage = self.usage_for_record(result, record_name)
            usage.all_fields.add(field_name)

            if is_condition:
                usage.condition_fields.add(field_name)

    def capture_dclgen_references(
        self,
        *,
        logical: str,
        result: FieldUsageAnalysis,
        is_condition: bool,
        is_output: bool,
    ) -> None:
        self._capture_dclgen_of_references(
            logical=logical,
            result=result,
            is_condition=is_condition,
            is_output=is_output,
        )
        self._capture_dclgen_dot_references(
            logical=logical,
            result=result,
            is_condition=is_condition,
            is_output=is_output,
        )

    def capture_move_usage(
        self,
        *,
        logical: str,
        result: FieldUsageAnalysis,
    ) -> None:
        match = MOVE_PATTERN.search(logical)

        if not match:
            return

        source_text = match.group("source")
        target_text = match.group("target")
        is_output = self._is_output_target(target_text)

        self._capture_move_source_usage(
            source_text=source_text,
            result=result,
            is_output=is_output,
        )
        self._capture_move_target_usage(
            target_text=target_text,
            result=result,
        )

    def usage_for_record(
        self,
        result: FieldUsageAnalysis,
        record_name: str,
    ) -> FieldUsage:
        record = NameNormalizer.normalize(record_name)

        if record not in result.usage_by_record:
            result.usage_by_record[record] = FieldUsage(record_name=record)

        return result.usage_by_record[record]

    def _capture_dclgen_of_references(
        self,
        *,
        logical: str,
        result: FieldUsageAnalysis,
        is_condition: bool,
        is_output: bool,
    ) -> None:
        for match in DCLGEN_OF_PATTERN.finditer(logical):
            field_name = NameNormalizer.to_cobol(match.group("field"))
            group_name = NameNormalizer.normalize(match.group("group"))
            record_name = self.group_to_record.get(group_name, "")

            if not field_name or not record_name:
                continue

            usage = self.usage_for_record(result, record_name)
            usage.dclgen_host_fields.add(field_name)

            if is_condition:
                usage.condition_fields.add(field_name)

            if is_output:
                usage.output_fields.add(field_name)

    def _capture_dclgen_dot_references(
        self,
        *,
        logical: str,
        result: FieldUsageAnalysis,
        is_condition: bool,
        is_output: bool,
    ) -> None:
        for match in DCLGEN_DOT_PATTERN.finditer(logical):
            field_name = NameNormalizer.to_cobol(match.group("field"))
            group_name = NameNormalizer.normalize(match.group("group"))
            record_name = self.group_to_record.get(group_name, "")

            if not field_name or not record_name:
                continue

            usage = self.usage_for_record(result, record_name)
            usage.dclgen_host_fields.add(field_name)

            if is_condition:
                usage.condition_fields.add(field_name)

            if is_output:
                usage.output_fields.add(field_name)

    def _capture_move_source_usage(
        self,
        *,
        source_text: str,
        result: FieldUsageAnalysis,
        is_output: bool,
    ) -> None:
        for source_match in QUALIFIED_REFERENCE_PATTERN.finditer(source_text):
            field_name = NameNormalizer.to_cobol(source_match.group("field"))
            record_name = NameNormalizer.normalize(source_match.group("record"))

            if not field_name or not record_name:
                continue

            if record_name.startswith(DCLGEN_GROUP_PREFIX):
                continue

            if record_name not in self.mapping_records:
                continue

            usage = self.usage_for_record(result, record_name)
            usage.move_source_fields.add(field_name)

            if is_output:
                usage.output_fields.add(field_name)

        self.capture_dclgen_references(
            logical=source_text,
            result=result,
            is_condition=False,
            is_output=is_output,
        )

    def _capture_move_target_usage(
        self,
        *,
        target_text: str,
        result: FieldUsageAnalysis,
    ) -> None:
        for target_match in QUALIFIED_REFERENCE_PATTERN.finditer(target_text):
            field_name = NameNormalizer.to_cobol(target_match.group("field"))
            record_name = NameNormalizer.normalize(target_match.group("record"))

            if not field_name or not record_name:
                continue

            if record_name.startswith(DCLGEN_GROUP_PREFIX):
                continue

            if record_name not in self.mapping_records:
                continue

            usage = self.usage_for_record(result, record_name)
            usage.move_target_fields.add(field_name)

    def _is_output_target(
        self,
        target_text: str,
    ) -> bool:
        upper_target = str(target_text or "").upper()

        return any(
            prefix in upper_target
            for prefix in OUTPUT_TARGET_PREFIXES
        )