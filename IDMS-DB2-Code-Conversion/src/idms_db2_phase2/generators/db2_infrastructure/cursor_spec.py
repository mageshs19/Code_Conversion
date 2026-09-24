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
    cursor_order: int = 0

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
    def read(
        cls,
        spec: dict[str, object],
        fallback_order: int = 0,
    ) -> "CursorSpec":
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
            cursor_order=cls._order(
                source.get("cursor_order"),
                fallback_order,
            ),
        )

    @classmethod
    def read_all(cls, specs: list[dict[str, object]]) -> list["CursorSpec"]:
        """Read every spec, preserving order.

        The list position is passed as the fallback order so that a spec
        dict built by an older path - one that never set "cursor_order" -
        still yields a DISTINCT order per cursor. Two cursors sharing an
        order would share a QUERYNO, and DB2 EXPLAIN could no longer tell
        their access paths apart.
        """
        return [
            cls.read(spec, fallback_order=index)
            for index, spec in enumerate(specs or [])
        ]
    
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
    
    @staticmethod
    def _order(value: object, fallback: int = 0) -> int:
        """Cursor position as a non-negative int, never raising.

        A missing, blank or non-numeric value falls back to the caller's
        list position rather than to a shared constant, so uniqueness
        survives a malformed spec.
        """
        try:
            order = int(str(value).strip())
        except (TypeError, ValueError):
            return max(0, int(fallback))

        return order if order >= 0 else max(0, int(fallback))