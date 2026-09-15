# LOCATION: src/idms_db2_phase2/resolvers/cursor_join_resolver.py
# ACTION: CREATE NEW FILE
"""Builds child-cursor WHERE predicates from IDMS set relationships.

The left operand is always a column of the CHILD table.
The right operand is always a host reference into the PARENT DCLGEN group.

    <child column> = :<parent group>.<parent host field>

Anything that cannot be resolved on the child side is dropped and reported,
never guessed. This honours CONVERSION_RULES:
"Do not fabricate DB2 SQL when Sheet Mapping metadata is missing."
"""

from __future__ import annotations

from idms_db2_phase2.resolvers.relationship_resolver import RelationshipResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.cursor_declaration_rules import CHILD_JOIN_PREDICATE_TEMPLATE


class CursorJoinResolver:
    """Resolves the WHERE clause of a child cursor."""

    def __init__(
        self,
        relationship_resolver: RelationshipResolver,
        column_name_resolver,
        host_variable_resolver,
    ) -> None:
        self.relationship_resolver = relationship_resolver
        self.column_name_resolver = column_name_resolver
        self.host_variable_resolver = host_variable_resolver
        self.diagnostics: list[str] = []

    # -----------------------------------------------------------------
    # Public entry point
    # -----------------------------------------------------------------
    def where_conditions(
        self,
        child_record: str,
    ) -> list[str]:
        """Return the join predicates for one child record."""
        self.diagnostics = []

        resolution = self.relationship_resolver.resolve(child_record)
        if resolution is None:
            return []

        self.diagnostics.extend(list(resolution.diagnostics or []))

        child_table = NameNormalizer.normalize(resolution.child_table)
        owned = {
            NameNormalizer.normalize(str(column)).upper()
            for column in self.column_name_resolver.columns_for_table(
                child_table
            )
        }

        conditions: list[str] = []
        seen: set[str] = set()

        for condition in list(resolution.conditions or []):
            predicate = self._predicate(condition, owned)
            if not predicate or predicate in seen:
                continue
            seen.add(predicate)
            conditions.append(predicate)

        return conditions

    # -----------------------------------------------------------------
    # One predicate
    # -----------------------------------------------------------------
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
            self.diagnostics.append(
                f"Cursor join: {child_column} is not a column of "
                f"{condition.child_table}; predicate skipped."
            )
            return ""

        group, host = self._parent_reference(condition)
        if not group or not host:
            self.diagnostics.append(
                f"Cursor join: no DCLGEN host variable for parent column "
                f"{getattr(condition, 'parent_column', '')}; predicate skipped."
            )
            return ""

        return CHILD_JOIN_PREDICATE_TEMPLATE.format(
            child_column=child_column,
            parent_group=group,
            parent_host=host,
        )

    # -----------------------------------------------------------------
    # Parent host reference -> (group, host)
    # -----------------------------------------------------------------
    def _parent_reference(self, condition) -> tuple[str, str]:
        """Split the canonical ':DCLGROUP.HOST-FIELD' form into parts."""
        reference = str(
            getattr(condition, "parent_host_reference", "") or ""
        ).strip()

        if not reference:
            reference = self.host_variable_resolver.host_reference_for_column(
                table_name=getattr(condition, "parent_table", ""),
                column_name=getattr(condition, "parent_column", ""),
            )

        reference = str(reference or "").strip().lstrip(":")
        if "." not in reference:
            return "", ""

        group, _, host = reference.partition(".")
        return (
            NameNormalizer.to_cobol(group.strip()),
            NameNormalizer.to_cobol(host.strip()),
        )