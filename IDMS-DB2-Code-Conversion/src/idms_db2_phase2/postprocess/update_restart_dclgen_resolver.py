from __future__ import annotations

from typing import Any, Optional

from idms_db2_phase2.postprocess.update_metadata_models import (
    DclgenRoleInfo,
    upper,
)
from idms_db2_phase2.postprocess.update_restart_dclgen_matcher import (
    UpdateRestartDclgenMatcher,
)
from idms_db2_phase2.postprocess.update_restart_dclgen_role_builder import (
    UpdateRestartDclgenRoleBuilder,
)
from idms_db2_phase2.postprocess.update_restart_dclgen_row_mapper import (
    UpdateRestartDclgenRowMapper,
)

# Substrings that identify a restart/control table by its DB2 table name.
# The restart table is a known DB2 object (e.g. DZ01RSTV / DZ01RSTB); its
# name always contains the "RST" control marker. This is a deterministic,
# rule-based identifier — no fuzzy scoring, no threshold.
RESTART_TABLE_NAME_HINTS = ("RST", "RESTART")


class UpdateRestartDclgenResolver:
    """
    Selects the restart DCLGEN group by TABLE NAME (deterministic) and
    delegates role-building.

    Rule-based design:
    - The DCLGEN parser already resolves the DB2 table name for each group.
    - The restart table is identified by its name (contains 'RST'/'RESTART').
    - No token scoring and no MIN_SCORE threshold are used.

    This class does not hardcode a specific restart table name; it matches the
    generic restart-control naming marker, so any DZxxRSTx table is detected.
    """

    def __init__(
        self,
        *,
        row_mapper: UpdateRestartDclgenRowMapper | None = None,
        role_builder: UpdateRestartDclgenRoleBuilder | None = None,
        matcher: UpdateRestartDclgenMatcher | None = None,
    ) -> None:
        self.row_mapper = row_mapper or UpdateRestartDclgenRowMapper()
        self.matcher = matcher or UpdateRestartDclgenMatcher()
        self.role_builder = role_builder or UpdateRestartDclgenRoleBuilder(
            row_mapper=self.row_mapper,
            matcher=self.matcher,
        )

    def resolve_restart_dclgen(
        self,
        dclgen_columns: list[Any],
        mapping_repository: Any | None = None,   # kept for signature compatibility
    ) -> Optional[DclgenRoleInfo]:
        groups = self._group_columns_by_dclgen(dclgen_columns)

        restart_group = self._find_restart_group_by_table_name(groups)
        if not restart_group:
            return None

        group_key, columns = restart_group
        return self.role_builder.build_restart_roles(
            group_key=group_key,
            columns=columns,
        )

    def _group_columns_by_dclgen(
        self,
        dclgen_columns: list[Any],
    ) -> dict[str, list[Any]]:
        """Group parsed DCLGEN columns by their resolved DB2 table name."""
        groups: dict[str, list[Any]] = {}

        for item in dclgen_columns:
            row = self.row_mapper.column_row(item)
            group_key = upper(row.get("table_name", ""))
            if not group_key:
                continue
            groups.setdefault(group_key, []).append(item)

        return groups

    def _find_restart_group_by_table_name(
        self,
        groups: dict[str, list[Any]],
    ) -> Optional[tuple[str, list[Any]]]:
        """Deterministically pick the restart DCLGEN group by table name.

        A group IS the restart table when its DB2 table name contains a
        restart-control marker ('RST' / 'RESTART'). No scoring, no threshold.
        """
        for group_key, columns in groups.items():
            table_name = upper(group_key)
            if any(hint in table_name for hint in RESTART_TABLE_NAME_HINTS):
                return group_key, columns

        return None


__all__ = [
    "UpdateRestartDclgenResolver",
    "RESTART_TABLE_NAME_HINTS",
]