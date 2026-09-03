from __future__ import annotations

from idms_db2_phase2.analyzers.field_usage_capture_service import (
    FieldUsageCaptureService,
)
from idms_db2_phase2.analyzers.field_usage_context_mapper import (
    FieldUsageContextMapper,
)
from idms_db2_phase2.analyzers.field_usage_models import (
    FieldUsage,
    FieldUsageAnalysis,
)
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from patterns.field_usage_analysis_patterns import (
    COMMENT_PATTERN,
    CONDITION_PATTERN,
    DIVISION_PATTERN,
    EXEC_SQL_END_PATTERN,
    EXEC_SQL_START_PATTERN,
)
from patterns.sequence_patterns import strip_sequence_numbers


class FieldUsageAnalyzer:
    """
    Generic COBOL field-usage analyzer.

    Detects:
    - IDMS qualified references: FIELD OF RECORD / FIELD IN RECORD
    - DCLGEN qualified references: FIELD OF DCLGROUP
    - DB2 host references: :DCLGROUP.FIELD / :FIELD OF DCLGROUP
    - MOVE source fields used for output
    - condition fields in IF / WHEN / UNTIL / EVALUATE

    This analyzer does not rewrite COBOL.
    """

    def __init__(
        self,
        mapping_repository: MappingRepository,
        table_name_resolver: TableNameResolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.table_name_resolver = table_name_resolver

        self.context_mapper = FieldUsageContextMapper(
            mapping_repository=mapping_repository,
            table_name_resolver=table_name_resolver,
        )

        self.mapping_records = self.context_mapper.mapping_records()
        self.group_to_record = self.context_mapper.group_to_record_map()

        self.capture_service = FieldUsageCaptureService(
            mapping_records=self.mapping_records,
            group_to_record=self.group_to_record,
        )

    def analyze(
        self,
        cobol_text: str,
    ) -> FieldUsageAnalysis:
        result = FieldUsageAnalysis()
        inside_procedure = False
        inside_exec_sql = False

        for line_number, raw_line in enumerate(
            str(cobol_text or "").splitlines(),
            start=1,
        ):
            logical = strip_sequence_numbers(raw_line).strip()

            if not logical:
                continue

            if COMMENT_PATTERN.match(logical):
                continue

            division_match = DIVISION_PATTERN.match(logical)

            if division_match:
                inside_procedure = division_match.group(1).upper() == "PROCEDURE"
                continue

            if EXEC_SQL_START_PATTERN.match(logical):
                inside_exec_sql = True

            if inside_exec_sql:
                self.capture_service.capture_dclgen_references(
                    logical=logical,
                    result=result,
                    is_condition=False,
                    is_output=False,
                )

                if EXEC_SQL_END_PATTERN.match(logical):
                    inside_exec_sql = False

                continue

            if not inside_procedure:
                continue

            is_condition = bool(CONDITION_PATTERN.match(logical))

            self.capture_service.capture_idms_qualified_references(
                logical=logical,
                result=result,
                is_condition=is_condition,
            )

            self.capture_service.capture_dclgen_references(
                logical=logical,
                result=result,
                is_condition=is_condition,
                is_output=False,
            )

            self.capture_service.capture_move_usage(
                logical=logical,
                result=result,
            )

        self._finalize_all_fields(result)
        self._append_diagnostics(result)

        return result

    def _finalize_all_fields(
        self,
        result: FieldUsageAnalysis,
    ) -> None:
        for usage in result.usage_by_record.values():
            usage.all_fields.update(usage.condition_fields)
            usage.all_fields.update(usage.output_fields)
            usage.all_fields.update(usage.move_source_fields)
            usage.all_fields.update(usage.move_target_fields)
            usage.all_fields.update(usage.dclgen_host_fields)

    def _append_diagnostics(
        self,
        result: FieldUsageAnalysis,
    ) -> None:
        result.diagnostics.append(
            "Field usage analyzer: records with usage detected: "
            f"{len(result.usage_by_record)}"
        )

        for record_name, usage in sorted(result.usage_by_record.items()):
            result.diagnostics.append(
                "Field usage analyzer: "
                f"record={record_name}, "
                f"condition={len(usage.condition_fields)}, "
                f"output={len(usage.output_fields)}, "
                f"move_source={len(usage.move_source_fields)}, "
                f"move_target={len(usage.move_target_fields)}, "
                f"dclgen={len(usage.dclgen_host_fields)}"
            )


__all__ = [
    "FieldUsage",
    "FieldUsageAnalysis",
    "FieldUsageAnalyzer",
]