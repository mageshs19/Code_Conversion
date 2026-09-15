# LOCATION: src/idms_db2_phase2/generators/db2_infrastructure/cursor_spec.py
# ACTION: CREATE NEW FILE

"""Typed, cleaned view of a cursor spec dictionary.

Db2InfrastructureGenerator builds specs as plain dicts. Every consumer
was re-normalising the same five keys, each with its own idea of what
"clean" meant. This value object does it once.

Column ORDER is authoritative. The FETCH INTO host list is built from
the same sequence, so a reordering here silently corrupts every fetched
row. De-duplication therefore preserves first-seen order and never
sorts.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from idms_db2_phase2.services.name_normalizer import NameNormalizer


@dataclass(frozen=True)
class CursorSpec:
    """One cursor, ready to render."""

    cursor_name: str = ""
    table_name: str = ""
    record_name: str = ""
    select_columns: list[str] = field(default_factory=list)
    where_conditions: list[str] = field(default_factory=list)
    order_by_columns: list[str] = field(default_factory=list)

    @property
    def is_declarable(self) -> bool:
        return bool(self.cursor_name and self.table_name)

    @property
    def is_child(self) -> bool:
        """A cursor with a WHERE clause is a child of another cursor."""
        return bool(self.where_conditions)

    @property
    def not_eoc_suffix_source(self) -> str:
        return self.cursor_name

    # =================================================================
    # Construction
    # =================================================================
    @classmethod
    def read(cls, spec: dict[str, object]) -> "CursorSpec":
        source = spec or {}

        return cls(
            cursor_name=NameNormalizer.to_cobol(
                str(source.get("cursor_name", ""))
            ),
            table_name=NameNormalizer.normalize(
                str(source.get("table_name", ""))
            ),
            record_name=NameNormalizer.normalize(
                str(source.get("record_name", ""))
            ),
            select_columns=cls._columns(source.get("select_columns")),
            where_conditions=cls._items(source.get("where_conditions")),
            order_by_columns=cls._items(source.get("order_by_columns")),
        )

    @classmethod
    def read_all(cls, specs: list[dict[str, object]]) -> list["CursorSpec"]:
        return [cls.read(spec) for spec in specs or []]

    # =================================================================
    # Cleaning
    # =================================================================
    @staticmethod
    def _columns(value: object) -> list[str]:
        """Normalised column names, de-duplicated, order preserved."""
        out: list[str] = []
        seen: set[str] = set()

        for column in list(value or []):
            normalized = NameNormalizer.normalize(str(column))
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            out.append(normalized)

        return out

    @staticmethod
    def _items(value: object) -> list[str]:
        """Trimmed free-text clause items, de-duplicated, order preserved."""
        out: list[str] = []
        seen: set[str] = set()

        for item in list(value or []):
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            out.append(text)

        return out