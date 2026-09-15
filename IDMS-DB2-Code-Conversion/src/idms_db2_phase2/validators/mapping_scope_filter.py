# LOCATION: src/idms_db2_phase2/validators/mapping_scope_filter.py
# ACTION: CREATE NEW FILE

"""Scopes mapping validation messages to the program being converted.

A Sheet Mapping gap is an ERROR only for a table the program actually
references. For every other table it is a workbook note, and reporting it
as a blocker makes a clean retrieval conversion read as Rejected.

Reference detection is deliberately conservative: a table counts as
referenced when its own name, or the IDMS record name mapped to it,
appears anywhere in the SOURCE program. No message is ever discarded -
out-of-scope gaps are rewritten, not hidden.
"""

from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.mapping_scope_patterns import (
    MESSAGE_TABLE_PATTERN,
    SOURCE_TOKEN_PATTERN,
)
from rules.mapping_scope_rules import (
    DIAG_SCOPE_APPLIED,
    ENFORCE_MAPPING_SCOPE_FILTER,
    OUT_OF_SCOPE_TEMPLATE,
)


class MappingScopeFilter:
    """Rewrites mapping gaps for tables the program does not reference."""

    def __init__(
        self,
        mapping_repository,
        table_name_resolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.table_name_resolver = table_name_resolver
        self.messages: list[str] = []

    # =================================================================
    # Public entry point
    # =================================================================
    def apply(
        self,
        messages: list[str],
        source_text: str,
    ) -> list[str]:
        self.messages = []

        if not messages or not ENFORCE_MAPPING_SCOPE_FILTER:
            return list(messages or [])

        referenced = self._referenced_tables(source_text)
        out: list[str] = []
        rewritten = 0
        gaps = 0

        for message in messages:
            table = self._table_of(message)

            if not table:
                out.append(message)
                continue

            gaps += 1

            if table in referenced:
                out.append(message)
                continue

            out.append(OUT_OF_SCOPE_TEMPLATE.format(table=table))
            rewritten += 1

        if rewritten:
            self.messages.append(
                DIAG_SCOPE_APPLIED.format(
                    out_of_scope=rewritten,
                    total=gaps,
                )
            )

        return out

    # =================================================================
    # Reference detection
    # =================================================================
    def _referenced_tables(self, source_text: str) -> set[str]:
        """Tables whose name or mapped record appears in the source."""
        tokens = {
            NameNormalizer.compact(match.group(0))
            for match in SOURCE_TOKEN_PATTERN.finditer(str(source_text or ""))
        }
        tokens.discard("")

        referenced: set[str] = set()

        for record in self._records():
            table = NameNormalizer.normalize(
                self.table_name_resolver.table_for_record(record)
            )
            if not table:
                continue

            if NameNormalizer.compact(table) in tokens:
                referenced.add(table)
                continue

            if NameNormalizer.compact(record) in tokens:
                referenced.add(table)

        return referenced

    def _records(self) -> list[str]:
        try:
            return [
                NameNormalizer.normalize(record)
                for record in self.mapping_repository.records()
            ]
        except Exception:  # noqa: BLE001
            return []

    @staticmethod
    def _table_of(message: str) -> str:
        match = MESSAGE_TABLE_PATTERN.search(str(message or ""))
        if not match:
            return ""
        return NameNormalizer.normalize(match.group("table"))