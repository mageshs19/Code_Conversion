from __future__ import annotations

from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.relationship_key_classifier import (
    RelationshipKeyClassifier,
)
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class RelationshipKeyColumnResolver:
    """
    Resolves primary-key, foreign-key, and order-by columns for records.
    """

    def __init__(
        self,
        *,
        mapping_repository: MappingRepository,
        classifier: RelationshipKeyClassifier | None = None,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.classifier = classifier or RelationshipKeyClassifier()

    def foreign_key_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        record = NameNormalizer.normalize(record_name)
        rows = self.mapping_repository.rows_for_record(record)
        output: list[str] = []
        seen: set[str] = set()

        for row in rows:
            if not self.classifier.is_foreign_key_row(row):
                continue

            column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
                or getattr(row, "cross_application_db2_field_name", "")
            )

            if not column or column in seen:
                continue

            seen.add(column)
            output.append(column)

        return output

    def primary_key_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        record = NameNormalizer.normalize(record_name)
        rows = self.mapping_repository.rows_for_record(record)
        output: list[str] = []
        seen: set[str] = set()

        for row in rows:
            if not self.classifier.is_primary_key_row(row):
                continue

            column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
            )

            if not column or column in seen:
                continue

            seen.add(column)
            output.append(column)

        return output

    def order_by_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        record = NameNormalizer.normalize(record_name)
        primary_keys = self.primary_key_columns_for_record(record)
        foreign_keys = set(self.foreign_key_columns_for_record(record))
        output: list[str] = []

        for column in primary_keys:
            normalized = NameNormalizer.normalize(column)

            if not normalized:
                continue

            if normalized in foreign_keys:
                continue

            if normalized not in output:
                output.append(normalized)

        return output

    def has_foreign_keys(
        self,
        record_name: str,
    ) -> bool:
        return bool(self.foreign_key_columns_for_record(record_name))