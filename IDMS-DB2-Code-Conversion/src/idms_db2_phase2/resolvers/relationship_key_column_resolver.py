from __future__ import annotations

from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.relationship_key_classifier import (
    RelationshipKeyClassifier,
)
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.cursor_declaration_rules import (
    CURSOR_ORDER_BY_MESSAGES,
    ORDER_BY_SOURCE_PRIMARY_KEY,
)

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
        self.messages: list[str] = []

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

# LOCATION: src/idms_db2_phase2/resolvers/relationship_key_column_resolver.py
# ACTION: REPLACE the order_by_columns_for_record method

    def order_by_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        """ORDER BY columns inferred from the record's own key.

        CORRECTION - the empty result was silent.

        An empty list meant "this cursor will not be ordered", which is a
        behavioural statement about the output file, and it was reported
        nowhere. The reader could not distinguish "the record genuinely
        has no ordering" from "the Sheet Mapping does not flag the key".

        The inference itself is unchanged: primary keys minus foreign
        keys, Sheet Mapping order preserved.
        """
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

        self._report_order_by(
            record=record,
            primary_keys=primary_keys,
            output=output,
        )
        return output

    def _report_order_by(
        self,
        *,
        record: str,
        primary_keys: list[str],
        output: list[str],
    ) -> None:
        """Say where the ORDER BY came from, or why there is none."""
        messages = getattr(self, "messages", None)
        if messages is None:
            self.messages = []
            messages = self.messages

        if output:
            messages.append(
                CURSOR_ORDER_BY_MESSAGES["resolved"].format(
                    record=record,
                    count=len(output),
                    source=ORDER_BY_SOURCE_PRIMARY_KEY,
                    columns=", ".join(output),
                )
            )
            return

        if primary_keys:
            messages.append(
                CURSOR_ORDER_BY_MESSAGES["empty_all_foreign"].format(
                    record=record
                )
            )
            return

        messages.append(
            CURSOR_ORDER_BY_MESSAGES["empty_no_primary_key"].format(
                record=record
            )
        )

    def has_foreign_keys(
        self,
        record_name: str,
    ) -> bool:
        return bool(self.foreign_key_columns_for_record(record_name))