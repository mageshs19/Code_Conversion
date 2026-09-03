from __future__ import annotations

from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.cursor_column_filter import CursorColumnFilter
from idms_db2_phase2.resolvers.relationship_resolver import RelationshipResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.cursor_column_rules import (
    DESC_HINT_WORDS,
    ORDER_HINT_WORDS,
)


class CursorOrderByResolver:
    """
    Resolves cursor ORDER BY columns.

    Parent cursors only receive ORDER BY when Sheet Mapping explicitly indicates
    order semantics. Child cursors use relationship-derived order columns.
    """

    def __init__(
        self,
        mapping_repository: MappingRepository,
        relationship_resolver: RelationshipResolver,
        column_filter: CursorColumnFilter,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.relationship_resolver = relationship_resolver
        self.column_filter = column_filter

    def order_by_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        record = NameNormalizer.normalize(record_name)

        if not record:
            return []

        is_child = self.relationship_resolver.has_foreign_keys(record)

        if not is_child:
            return self.explicit_parent_order_columns(record)

        order_columns = self.order_by_base_columns_for_record(record)
        output: list[str] = []

        for column in order_columns:
            expression = column

            if self.should_order_desc(
                record_name=record,
                column_name=column,
            ):
                expression = f"{column} DESC"

            output.append(expression)

        return self.column_filter.unique(output)

    def explicit_parent_order_columns(
        self,
        record_name: str,
    ) -> list[str]:
        """
        Parent/root cursor gets ORDER BY only if Sheet Mapping explicitly
        indicates order/sort/rank semantics.
        """

        rows = self.mapping_repository.rows_for_record(record_name)
        output: list[str] = []

        for row in rows:
            text = " ".join(
                [
                    str(getattr(row, "remarks", "") or ""),
                    str(getattr(row, "hopex_expression_type_remark", "") or ""),
                    str(getattr(row, "relation", "") or ""),
                    str(getattr(row, "basetype", "") or ""),
                ]
            ).upper()

            if not any(word in text for word in ORDER_HINT_WORDS):
                continue

            column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
            )

            if not column:
                continue

            if not self.column_filter.column_exists_for_record(record_name, column):
                continue

            if self.column_filter.is_audit_column(column):
                continue

            output.append(column)

        return self.column_filter.unique(output)

    def order_by_base_columns_for_record(
        self,
        record_name: str,
    ) -> list[str]:
        return self.relationship_resolver.order_by_columns_for_record(record_name)

    def should_order_desc(
        self,
        record_name: str,
        column_name: str,
    ) -> bool:
        record = NameNormalizer.normalize(record_name)
        column = NameNormalizer.normalize(column_name)

        rows = self.mapping_repository.rows_for_record(record)

        for row in rows:
            row_column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
            )

            if row_column != column:
                continue

            combined_text = " ".join(
                [
                    str(getattr(row, "db2_key", "") or ""),
                    str(getattr(row, "hopex_expression_type_remark", "") or ""),
                    str(getattr(row, "remarks", "") or ""),
                    str(getattr(row, "new_db2_data_type", "") or ""),
                    str(getattr(row, "basetype", "") or ""),
                    column,
                ]
            ).upper()

            if any(word in combined_text for word in DESC_HINT_WORDS):
                return True

        return False