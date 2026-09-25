# LOCATION: src/idms_db2_phase2/resolvers/cursor_join_resolver.py
# ACTION: REPLACE ENTIRE FILE
"""Builds child-cursor WHERE predicates from IDMS set relationships.

The left operand is always a column of the CHILD table.
The right operand is always a host reference into a PARENT DCLGEN group.

    <child column> = :<parent group>.<parent host field>

Anything that cannot be resolved on BOTH sides is dropped and reported,
never guessed. This honours CONVERSION_RULES:
"Do not fabricate DB2 SQL when Sheet Mapping metadata is missing."

CORRECTION 1 - fallback constants were never imported (NameError).
CORRECTION 2 - host_for_column() does not exist on HostVariableResolver.
               The API is host_reference_for_column() + group_for_table().
CORRECTION 3 - the fallback compared a column to its OWN DCLGEN group,
               which is not a join. The parent side is now resolved from
               the relationship, or supplied explicitly by the caller
               (LRF path keyword), or the predicate is refused.
CORRECTION 4 - the facade exposes resolve() on some paths and
               resolve_for_child_record() on others; both are tolerated.
"""

from __future__ import annotations

from idms_db2_phase2.resolvers.relationship_resolver import RelationshipResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.cursor_declaration_rules import (
    CHILD_JOIN_PREDICATE_TEMPLATE,
    DRIVING_KEY_PREDICATE_TEMPLATE,
    EMIT_DRIVING_KEY_PREDICATE,
    JOIN_MESSAGES,
)

HOST_PREFIX = ":"
GROUP_SEPARATOR = "."


class CursorJoinResolver:
    """Resolves the WHERE clause of a child cursor."""

    def __init__(
        self,
        relationship_resolver: RelationshipResolver,
        column_name_resolver,
        host_variable_resolver,
        table_name_resolver=None,
    ) -> None:
        self.relationship_resolver = relationship_resolver
        self.column_name_resolver = column_name_resolver
        self.host_variable_resolver = host_variable_resolver

        # Injected when available; otherwise read off the facade, which
        # holds the same instance. Never constructed here.
        self.table_name_resolver = table_name_resolver or getattr(
            relationship_resolver, "table_name_resolver", None
        )
        self.diagnostics: list[str] = []

    # =================================================================
    # Public entry point
    # =================================================================
    def where_conditions(
        self,
        child_record: str,
        driving_host_reference: str = "",
    ) -> list[str]:
        """Join predicates for one child record.

        Three ordered attempts, every failure reported:

          1. relationship predicates  (foreign-key rows)
          2. driving-key predicates   (parent host, or a caller-supplied
                                       driving host from the LRF path)
          3. refuse, and say so
        """
        self.diagnostics = []

        record = NameNormalizer.normalize(child_record)
        if not record:
            return []

        resolution = self._resolve(record)

        if resolution is None:
            self._log("no_resolution", record=record)
            return self._driving_key_conditions(
                child_record=record,
                resolution=None,
                driving_host_reference=driving_host_reference,
            )

        self.diagnostics.extend(list(getattr(resolution, "diagnostics", []) or []))

        child_table = NameNormalizer.normalize(
            getattr(resolution, "child_table", "")
        )
        owned = self._owned_columns(child_table)

        conditions: list[str] = []
        seen: set[str] = set()

        for condition in list(getattr(resolution, "conditions", []) or []):
            predicate = self._predicate(condition, owned)
            if not predicate or predicate in seen:
                continue
            seen.add(predicate)
            conditions.append(predicate)

        if conditions:
            return conditions

        # Attempt 2: no usable foreign-key predicate was produced.
        self._log("no_fk_rows", record=record)
        return self._driving_key_conditions(
            child_record=record,
            resolution=resolution,
            driving_host_reference=driving_host_reference,
        )

    # =================================================================
    # Attempt 1 - one relationship predicate
    # =================================================================
    def _predicate(
        self,
        condition,
        owned: set[str],
    ) -> str:
        child_column = NameNormalizer.normalize(
            getattr(condition, "child_column", "")
        )
        if not child_column:
            return ""

        if owned and child_column.upper() not in owned:
            self._log(
                "unowned_column",
                column=child_column,
                table=NameNormalizer.normalize(
                    getattr(condition, "child_table", "")
                ),
            )
            return ""

        group, host = self._parent_reference(condition)
        if not group or not host:
            self._log(
                "no_parent_host",
                column=NameNormalizer.normalize(
                    getattr(condition, "parent_column", "")
                ),
            )
            return ""

        return CHILD_JOIN_PREDICATE_TEMPLATE.format(
            child_column=child_column,
            parent_group=group,
            parent_host=host,
        )

    # =================================================================
    # Attempt 2 - driving-key fallback
    # =================================================================
    def _driving_key_conditions(
        self,
        child_record: str,
        resolution,
        driving_host_reference: str = "",
    ) -> list[str]:
        """Qualify on the child's own key against a PARENT host.

        Refuses - loudly - when the parent side cannot be resolved
        deterministically. A predicate is never built against the
        child's own DCLGEN group.
        """
        if not EMIT_DRIVING_KEY_PREDICATE:
            return []

        child = NameNormalizer.normalize(child_record)
        child_table = self._table_for_record(child)

        if not child_table:
            self._log("no_child_table", record=child)
            return []

        parent_table = NameNormalizer.normalize(
            getattr(resolution, "parent_table", "") if resolution else ""
        )
        supplied_group, supplied_host = self._split_reference(
            driving_host_reference
        )

        if not parent_table and not supplied_group:
            self._log("no_parent_side", record=child)
            self._log("sweep", record=child)
            return []

        owned = self._owned_columns(child_table)
        key_columns = self._primary_key_columns(child)

        conditions: list[str] = []
        seen: set[str] = set()

        for column in key_columns or []:
            child_column = NameNormalizer.normalize(column)
            if not child_column:
                continue

            if owned and child_column.upper() not in owned:
                self._log(
                    "unowned_column",
                    column=child_column,
                    table=child_table,
                )
                continue

            if parent_table:
                group, host = self._split_reference(
                    self._host_reference(parent_table, child_column)
                )
            else:
                group, host = supplied_group, supplied_host

            if not group or not host:
                self._log("no_parent_host", column=child_column)
                continue

            predicate = DRIVING_KEY_PREDICATE_TEMPLATE.format(
                child_column=child_column,
                parent_group=group,
                parent_host=host,
            )
            if predicate in seen:
                continue
            seen.add(predicate)
            conditions.append(predicate)

        if not conditions:
            self._log("sweep", record=child)

        return conditions

    # =================================================================
    # Resolver compatibility
    # =================================================================
    def _resolve(self, child_record: str):
        """resolve() on some paths, resolve_for_child_record() on others."""
        for name in ("resolve", "resolve_for_child_record"):
            method = getattr(self.relationship_resolver, name, None)
            if callable(method):
                try:
                    return method(child_record)
                except TypeError:
                    continue
        return None

    def _table_for_record(self, record: str) -> str:
        resolver = self.table_name_resolver
        if resolver is None:
            return ""
        try:
            return NameNormalizer.normalize(resolver.table_for_record(record))
        except Exception:  # noqa: BLE001
            return ""

    def _primary_key_columns(self, record: str) -> list[str]:
        resolver = getattr(
            self.relationship_resolver, "key_column_resolver", None
        )
        method = getattr(resolver, "primary_key_columns_for_record", None)
        if not callable(method):
            return []
        try:
            return list(method(record) or [])
        except Exception:  # noqa: BLE001
            return []

    def _owned_columns(self, table: str) -> set[str]:
        if not table:
            return set()
        try:
            columns = self.column_name_resolver.columns_for_table(table)
        except Exception:  # noqa: BLE001
            return set()
        return {
            NameNormalizer.normalize(str(column)).upper()
            for column in (columns or [])
            if str(column or "").strip()
        }

    def _host_reference(self, table: str, column: str) -> str:
        try:
            return self.host_variable_resolver.host_reference_for_column(
                table_name=table,
                column_name=column,
            )
        except Exception:  # noqa: BLE001
            return ""

    # =================================================================
    # Parent host reference -> (group, host)
    # =================================================================
    def _parent_reference(self, condition) -> tuple[str, str]:
        reference = str(
            getattr(condition, "parent_host_reference", "") or ""
        ).strip()

        if not reference:
            reference = self._host_reference(
                NameNormalizer.normalize(getattr(condition, "parent_table", "")),
                NameNormalizer.normalize(getattr(condition, "parent_column", "")),
            )

        return self._split_reference(reference)

    @staticmethod
    def _split_reference(reference: str) -> tuple[str, str]:
        """Split the canonical ':DCLGROUP.HOST-FIELD' form into parts."""
        text = str(reference or "").strip().lstrip(HOST_PREFIX)
        if GROUP_SEPARATOR not in text:
            return "", ""

        group, _sep, host = text.partition(GROUP_SEPARATOR)
        group = NameNormalizer.to_cobol(group.strip())
        host = NameNormalizer.to_cobol(host.strip())

        if not group or not host:
            return "", ""
        return group, host

    # =================================================================
    # Diagnostics
    # =================================================================
    def _log(self, key: str, **values) -> None:
        template = JOIN_MESSAGES.get(key, "")
        if template:
            self.diagnostics.append(template.format(**values))


__all__ = ["CursorJoinResolver"]