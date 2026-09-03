from __future__ import annotations

from typing import Any

from catalogs.dclgen_schema import DCLGEN_GROUP_PREFIX
from idms_db2_phase2.postprocess.restart_role.restart_role_factory import (
    RestartRoleFactory,
)
from idms_db2_phase2.postprocess.restart_role.restart_role_field_resolver import (
    RestartRoleFieldResolver,
)
from idms_db2_phase2.postprocess.update_metadata_models import DclgenRoleInfo
from idms_db2_phase2.postprocess.update_restart_dclgen_matcher import (
    UpdateRestartDclgenMatcher,
)
from idms_db2_phase2.postprocess.update_restart_dclgen_row_mapper import (
    UpdateRestartDclgenRowMapper,
)
from rules.update_restart_rules import (
    RESTART_PAYLOAD_FALLBACK_TOKEN_KEY,
    RESTART_PAYLOAD_LENGTH_SPEC,
    RESTART_PAYLOAD_TEXT_SPEC,
    RESTART_PAYLOAD_TOKEN_KEY,
    RESTART_ROLE_COLUMN_FIELD_SPEC,
)


class UpdateRestartDclgenRoleBuilder(
    RestartRoleFieldResolver,
    RestartRoleFactory,
):
    """Builds DclgenRoleInfo from the selected restart DCLGEN column group.

    Generic: no restart table names, DCLGEN names, or host variable names are
    hardcoded. VARCHAR LEN/TEXT child fields are derived from the resolved
    payload group. Field/column resolution and role construction are provided
    by mixins; the role-key spec lives in rules/update_restart_rules.py.
    """

    def __init__(
        self,
        *,
        row_mapper: UpdateRestartDclgenRowMapper | None = None,
        matcher: UpdateRestartDclgenMatcher | None = None,
    ) -> None:
        self.row_mapper = row_mapper or UpdateRestartDclgenRowMapper()
        self.matcher = matcher or UpdateRestartDclgenMatcher()

    def build_restart_roles(
        self,
        *,
        group_key: str,
        columns: list[Any],
    ) -> DclgenRoleInfo:
        rows = [self.row_mapper.column_row(item) for item in columns]

        table_name = self.row_mapper.first_value(rows, "table_name") or group_key
        include_name = (
            self.row_mapper.first_value(rows, "include_name") or table_name
        )
        host_record = self.row_mapper.first_value(rows, "host_record")
        if not host_record and table_name:
            host_record = f"{DCLGEN_GROUP_PREFIX}{table_name}"

        payload_group = self._resolve_payload_group(rows)
        payload_len_field = self._resolve_payload_child_field(
            rows=rows,
            payload_group=payload_group,
            token_key=RESTART_PAYLOAD_LENGTH_SPEC[0],
            fallback_token_key=RESTART_PAYLOAD_LENGTH_SPEC[1],
            suffix_key=RESTART_PAYLOAD_LENGTH_SPEC[2],
        )
        payload_text_field = self._resolve_payload_child_field(
            rows=rows,
            payload_group=payload_group,
            token_key=RESTART_PAYLOAD_TEXT_SPEC[0],
            fallback_token_key=RESTART_PAYLOAD_TEXT_SPEC[1],
            suffix_key=RESTART_PAYLOAD_TEXT_SPEC[2],
        )

        # Resolve every (column, field) role pair from the spec in one loop.
        resolved: dict[str, str] = {}
        for role, (token_key, fallback_key) in RESTART_ROLE_COLUMN_FIELD_SPEC.items():
            resolved[f"{role}_col"] = self._find_column(
                rows=rows, token_key=token_key, fallback_token_key=fallback_key
            )
            resolved[f"{role}_field"] = self._find_field(
                rows=rows, token_key=token_key, fallback_token_key=fallback_key
            )

        payload_col = self._find_column(
            rows=rows,
            token_key=RESTART_PAYLOAD_TOKEN_KEY,
            fallback_token_key=RESTART_PAYLOAD_FALLBACK_TOKEN_KEY,
        )

        return self._make_role(
            table_name=table_name,
            include_name=include_name,
            host_record_name=host_record,
            host_record=host_record,
            program_column=resolved["program_col"],
            program_col=resolved["program_col"],
            program_field=resolved["program_field"],
            phase_column=resolved["phase_col"],
            phase_col=resolved["phase_col"],
            phase_field=resolved["phase_field"],
            date_column=resolved["date_col"],
            date_col=resolved["date_col"],
            date_field=resolved["date_field"],
            status_column=resolved["status_col"],
            status_col=resolved["status_col"],
            status_field=resolved["status_field"],
            retention_column=resolved["retention_col"],
            retention_col=resolved["retention_col"],
            retention_field=resolved["retention_field"],
            payload_column=payload_col,
            payload_col=payload_col,
            payload_group=payload_group,
            payload_group_field=payload_group,
            payload_len_field=payload_len_field,
            payload_length_field=payload_len_field,
            payload_text_field=payload_text_field,
        )