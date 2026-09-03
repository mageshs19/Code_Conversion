from __future__ import annotations

from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from idms_db2_phase2.transformers.field_reference.field_reference_field_extractor import (
    FieldReferenceFieldExtractor,
)
from idms_db2_phase2.transformers.field_reference.field_reference_host_resolver import (
    FieldReferenceHostResolver,
)
from rules.field_reference_rewriter_rules import DCLGEN_GROUP_PREFIX


class FieldReferenceContextBuilder:
    """Builds record-to-field and record-to-DCLGEN context maps from Sheet
    Mapping and DCLGEN metadata.

    Orchestration only. Field-name parsing is delegated to
    FieldReferenceFieldExtractor and host-reference formatting to
    FieldReferenceHostResolver.
    """

    def __init__(
        self,
        *,
        mapping_repository: MappingRepository,
        table_name_resolver: TableNameResolver,
        host_variable_resolver: HostVariableResolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.table_name_resolver = table_name_resolver
        self.host_variable_resolver = host_variable_resolver
        self._extractor = FieldReferenceFieldExtractor()
        self._host_resolver = FieldReferenceHostResolver(host_variable_resolver)

    def build_reference_maps(
        self,
    ) -> tuple[
        dict[str, dict[str, str]],
        dict[str, str],
        dict[str, str],
        dict[str, str],
    ]:
        record_field_map: dict[str, dict[str, str]] = {}
        record_group_map: dict[str, str] = {}
        table_record_map: dict[str, str] = {}
        group_record_map: dict[str, str] = {}

        for record in self.mapping_repository.records():
            normalized_record = NameNormalizer.normalize(record)
            if not normalized_record:
                continue

            resolved_table = self.table_name_resolver.table_for_record(
                normalized_record
            )

            if resolved_table:
                table_key = NameNormalizer.normalize(resolved_table)
                group_name = DCLGEN_GROUP_PREFIX + NameNormalizer.to_cobol(table_key)

                record_group_map[normalized_record] = group_name
                table_record_map[table_key] = normalized_record
                group_record_map[NameNormalizer.normalize(group_name)] = (
                    normalized_record
                )

            record_field_map[normalized_record] = self.field_map_for_record(
                normalized_record
            )

        self.add_redefines_aliases(record_field_map)

        return (
            record_field_map,
            record_group_map,
            table_record_map,
            group_record_map,
        )

    def field_map_for_record(self, record_name: str) -> dict[str, str]:
        output: dict[str, str] = {}
        rows = self.mapping_repository.rows_for_record(record_name)

        for row in rows:
            source_candidates = self.source_candidates_from_row(row)
            if not source_candidates:
                continue

            target_table = self.table_name_resolver.resolve_table(
                self._extractor.first_non_empty(
                    getattr(row, "new_db2_record", ""),
                    getattr(row, "cross_application_db2_table", ""),
                )
            )
            target_column = NameNormalizer.normalize(
                self._extractor.first_non_empty(
                    getattr(row, "new_db2_field_name", ""),
                    getattr(row, "cross_application_db2_field_name", ""),
                )
            )

            if not target_table or not target_column:
                continue

            target_reference = self._host_resolver.dclgen_reference_for_column(
                table_name=target_table,
                column_name=target_column,
            )
            if not target_reference:
                continue

            for source_candidate in source_candidates:
                source_key = self._extractor.field_key(source_candidate)
                if not source_key:
                    continue
                if source_key not in output:
                    output[source_key] = target_reference

        return output

    def source_candidates_from_row(self, row) -> list[str]:
        candidates: list[str] = []

        for value in [
            getattr(row, "cobol_zone", ""),
            getattr(row, "reference_field_name_copybook", ""),
        ]:
            field_name = self._extractor.extract_field_name(value)
            if not field_name:
                continue

            cobol_name = NameNormalizer.to_cobol(field_name)
            if cobol_name and cobol_name not in candidates:
                candidates.append(cobol_name)

            redefines_base = self._extractor.extract_redefines_base(value)
            if redefines_base:
                base_name = NameNormalizer.to_cobol(redefines_base)
                if base_name and base_name not in candidates:
                    candidates.append(base_name)

        return candidates

    def add_redefines_aliases(
        self,
        record_field_map: dict[str, dict[str, str]],
    ) -> None:
        for record in self.mapping_repository.records():
            normalized_record = NameNormalizer.normalize(record)
            rows = self.mapping_repository.rows_for_record(normalized_record)
            field_map = record_field_map.get(normalized_record, {})
            if not field_map:
                continue

            for row in rows:
                cobol_zone = getattr(row, "cobol_zone", "") or ""
                alias_name = self._extractor.extract_field_name(cobol_zone)
                base_name = self._extractor.extract_redefines_base(cobol_zone)
                if not alias_name or not base_name:
                    continue

                alias_key = self._extractor.field_key(alias_name)
                base_key = self._extractor.field_key(base_name)
                if not alias_key or not base_key:
                    continue
                if alias_key in field_map:
                    continue
                if base_key in field_map:
                    field_map[alias_key] = field_map[base_key]