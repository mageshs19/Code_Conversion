from __future__ import annotations

from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.field_reference_rewriter_patterns import (
    HOST_REFERENCE_DOT_PATTERN,
    HOST_REFERENCE_OF_PATTERN,
    HOST_REFERENCE_OF_SPLIT_PATTERN,
)
from rules.field_reference_rewriter_rules import (
    HOST_GROUP_SEPARATOR,
    HOST_OF_GROUP_TEMPLATE,
    HOST_OF_SPLIT_PART_COUNT,
    HOST_REFERENCE_LEADING_CHAR,
)


class FieldReferenceHostResolver:
    """Resolves and formats a DCLGEN host reference for a DB2 column.

    Produces the canonical "HOST OF GROUP" form. No inline regex and no
    hardcoded separators live here; all patterns and literals are external.
    """

    def __init__(self, host_variable_resolver: HostVariableResolver) -> None:
        self.host_variable_resolver = host_variable_resolver

    def dclgen_reference_for_column(
        self,
        *,
        table_name: str,
        column_name: str,
    ) -> str:
        host_reference = self.host_variable_resolver.host_reference_for_column(
            table_name=table_name,
            column_name=column_name,
        )

        if not host_reference:
            return ""

        host_reference = str(host_reference or "").strip()

        of_match = HOST_REFERENCE_OF_PATTERN.search(host_reference)
        if of_match:
            return self._format(of_match.group("host"), of_match.group("group"))

        dot_match = HOST_REFERENCE_DOT_PATTERN.search(host_reference)
        if dot_match:
            return self._format(dot_match.group("host"), dot_match.group("group"))

        cleaned = host_reference.lstrip(HOST_REFERENCE_LEADING_CHAR).strip()

        if HOST_GROUP_SEPARATOR in cleaned.upper():
            parts = HOST_REFERENCE_OF_SPLIT_PATTERN.split(cleaned)
            if len(parts) == HOST_OF_SPLIT_PART_COUNT:
                return self._format(parts[0], parts[1])

        return NameNormalizer.to_cobol(cleaned)

    def _format(self, host: str, group: str) -> str:
        return HOST_OF_GROUP_TEMPLATE.format(
            host=NameNormalizer.to_cobol(host),
            group=NameNormalizer.to_cobol(group),
        )