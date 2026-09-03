from __future__ import annotations

from typing import Any

from idms_db2_phase2.services.name_normalizer import NameNormalizer


class RelationshipKeyClassifier:
    """
    Classifies Sheet Mapping rows as primary-key or foreign-key rows.
    """

    def is_primary_key_row(
        self,
        row: Any,
    ) -> bool:
        db2_key = NameNormalizer.normalize(getattr(row, "db2_key", ""))
        idms_key = NameNormalizer.normalize(getattr(row, "idms_key", ""))

        return (
            "PRIMARY" in db2_key
            or db2_key == "KEY"
            or "CALC" in idms_key
        )

    def is_foreign_key_row(
        self,
        row: Any,
    ) -> bool:
        db2_key = NameNormalizer.normalize(getattr(row, "db2_key", ""))
        relation = NameNormalizer.normalize(getattr(row, "relation", ""))

        return (
            "FOREIGN" in db2_key
            or "FK" in db2_key
            or "FOREIGN" in relation
        )