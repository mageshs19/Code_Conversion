from __future__ import annotations

from idms_db2_phase2.analyzers.field_usage_analyzer import FieldUsageAnalysis
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class CursorFieldUsageColumnSelector:
    """
    Resolves cursor SELECT columns from procedure field usage.

    This helper maps COBOL source fields or DCLGEN host fields back to DB2
    columns using Sheet Mapping metadata.
    """

    def __init__(
        self,
        mapping_repository: MappingRepository,
    ) -> None:
        self.mapping_repository = mapping_repository

    def columns_from_field_usage(
        self,
        record_name: str,
        field_usage_analysis: FieldUsageAnalysis | None,
    ) -> list[str]:
        if field_usage_analysis is None:
            return []

        usage = field_usage_analysis.usage_by_record.get(
            NameNormalizer.normalize(record_name)
        )

        if usage is None:
            return []

        output: list[str] = []

        # Sort the field set so SELECT/FETCH column order is deterministic
        # run-to-run (a set iterates in a hash-seed-dependent order).
        for field_name in sorted(usage.all_fields):
            column = self.column_for_source_or_host_field(
                record_name=record_name,
                source_or_host_field=field_name,
            )

            if column:
                output.append(column)

        return self._unique(output)

    def column_for_source_or_host_field(
        self,
        record_name: str,
        source_or_host_field: str,
    ) -> str:
        record = NameNormalizer.normalize(record_name)
        source = NameNormalizer.normalize(source_or_host_field)

        if not record or not source:
            return ""

        rows = self.mapping_repository.rows_for_record(record)

        for row in rows:
            target_column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
                or getattr(row, "cross_application_db2_field_name", "")
            )

            if not target_column:
                continue

            source_candidates = {
                NameNormalizer.normalize(
                    self.extract_source_field(getattr(row, "cobol_zone", ""))
                ),
                NameNormalizer.normalize(
                    self.extract_source_field(
                        getattr(row, "reference_field_name_copybook", "")
                    )
                ),
                target_column,
                NameNormalizer.normalize(NameNormalizer.to_cobol(target_column)),
            }

            source_candidates = {
                candidate
                for candidate in source_candidates
                if candidate
            }

            if source in source_candidates:
                return target_column

        return ""

    def extract_source_field(
        self,
        value: str,
    ) -> str:
        text = str(value or "").strip()

        if not text:
            return ""

        text = text.replace(".", " ")
        tokens = text.split()

        if tokens and tokens[0].isdigit() and len(tokens) > 1:
            return tokens[1]

        if tokens:
            return tokens[0]

        return ""

    def _unique(
        self,
        values: list[str],
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for value in values:
            normalized = NameNormalizer.normalize(value)

            if not normalized:
                continue

            if normalized in seen:
                continue

            seen.add(normalized)
            output.append(normalized)

        return output