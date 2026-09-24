# LOCATION: src/idms_db2_phase2/composers/record_materialisation/record_plan_builder.py
# ACTION: CREATE NEW FILE
"""Assembles a RecordMaterialisationPlan from Sheet Mapping rows.

Orchestration only:

    record_row_reader.py       reads each row
    record_host_resolver.py    resolves the DCLGEN host
    record_field.py            answers the policy questions
    record_plan.py             holds the result

CORRECTION B + C - what counts as 'missing'

    A field is missing ONLY when it carries a REAL DB2 column that
    DCLGEN does not define. No column at all means COBOL filler or the
    breakdown of a mapped parent, and must never block the record.
"""

from __future__ import annotations

from idms_db2_phase2.composers.record_materialisation.record_host_resolver import (
    RecordHostResolver,
)
from idms_db2_phase2.composers.record_materialisation.record_plan import (
    RecordMaterialisationPlan,
)
from idms_db2_phase2.composers.record_materialisation.record_row_reader import (
    RecordRowReader,
)
from rules.record_materialisation_rules import NON_RECORD_NAME_SUFFIXES


class RecordPlanBuilder:
    """Turns Sheet Mapping rows into a RecordMaterialisationPlan."""

    def __init__(
        self,
        *,
        mapping_repository,
        table_name_resolver,
        host_variable_resolver,
        row_reader: RecordRowReader | None = None,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.rows_reader = row_reader or RecordRowReader()
        self.hosts = RecordHostResolver(
            table_name_resolver=table_name_resolver,
            host_variable_resolver=host_variable_resolver,
        )

    # ----------------------------------------------------------- public
    def build(self, record_name: str) -> RecordMaterialisationPlan:
        record = self.cobol_name(record_name)
        plan = RecordMaterialisationPlan(record_name=record)

        rows = self._rows(record)
        if not rows:
            return plan

        plan.table_name = self.hosts.table_for(record)
        plan.group_name = self.hosts.group_for(plan.table_name)

        for row in rows:
            item = self.rows_reader.read(row)

            if item is None:
                plan.skipped_rows += 1
                continue

            # Only a REAL column is ever looked up. FILLER, a blank
            # cell, a REDEFINES and the unmapped subordinates of a
            # mapped group are never queried.
            if item.requires_host:
                item.host_reference = self.hosts.host_for(
                    plan.table_name,
                    item.db2_column,
                )

            plan.fields.append(item)

            if item.is_missing_host:
                plan.missing_hosts.append(item.name)

        return plan

    @staticmethod
    def looks_like_record(name: str) -> bool:
        """Guard so a LINKAGE work field such as DATE8-LS is not treated
        as a mapped IDMS record. Suffix driven, so no name is hardcoded.
        """
        candidate = str(name or "").strip().upper()
        if not candidate:
            return False
        return not candidate.endswith(NON_RECORD_NAME_SUFFIXES)

    # ---------------------------------------------------------- helpers
    def _rows(self, record: str) -> list:
        try:
            return list(
                self.mapping_repository.rows_for_record(record) or []
            )
        except Exception:  # noqa: BLE001
            return []

    @staticmethod
    def cobol_name(value: str) -> str:
        return str(value or "").strip().upper().replace("_", "-")


__all__ = ["RecordPlanBuilder"]