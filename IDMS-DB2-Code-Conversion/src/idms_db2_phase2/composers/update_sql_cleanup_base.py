# LOCATION: src/idms_db2_phase2/composers/update_sql_cleanup_base.py
# ACTION: CREATE NEW FILE (this replaces update_program_feedback_shared.py)

"""
Shared base for update-program SQL cleanup composers.

Generic rules:
- Sheet Mapping is authority for DB2 tables and columns.
- DCLGEN is authority for host variable spelling.
- Do not hardcode program names, table names, columns, or host variables.
- For CALC/update flows, prefer DB2 primary-key metadata.
- Avoid broad WHERE clauses when a narrower DB2 identity key is available.

Source-field resolution is deterministic (delegated to the Sheet Mapping
repository). No fuzzy / similarity matching.

This base composes focused mixins so subclasses keep the exact same inherited
interface (self._logical, self._db2_primary_key_columns, self._set_lines,
self._column_for_source_field, ...) and the same class-level regex/constant
attributes.
"""

from __future__ import annotations

from idms_db2_phase2.composers.update_sql_cleanup.column_mixin import (
    ColumnMixin,
)
from idms_db2_phase2.composers.update_sql_cleanup.key_column_mixin import (
    KeyColumnMixin,
)
from idms_db2_phase2.composers.update_sql_cleanup.scan_mixin import ScanMixin
from idms_db2_phase2.composers.update_sql_cleanup.sql_line_mixin import (
    SqlLineMixin,
)
from idms_db2_phase2.composers.update_sql_cleanup.update_sql_cleanup_patterns import (
    CONVERTED_MODIFY_PATTERN,
    CONVERTED_OBTAIN_CALC_PATTERN,
    END_IF_PATTERN,
    EXEC_SQL_END_PATTERN,
    EXEC_SQL_START_PATTERN,
    INCLUDE_PATTERN,
    LINKAGE_SECTION_PATTERN,
    MALFORMED_SQLERROR_ENDIF_PATTERN,
    MOVE_TO_BARE_FIELD_PATTERN,
    MOVE_TO_DCL_HOST_PATTERN,
    SQL_LOCATION_PATTERN,
    SQLCODE_IF_PATTERN,
    STOP_RUN_PATTERN,
    TIMESTAMP_PARAGRAPH_PATTERN,
)
from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.host_variable_resolver import (
    HostVariableResolver,
)
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from rules.update_sql_cleanup_rules import (
    IDENTITY_KEY_PREFIXES,
    INSERT_ONLY_AUDIT_PREFIXES,
    PROTECTED_BARE_TARGET_PREFIXES,
    UPDATE_AUDIT_PREFIXES,
)


class UpdateSqlCleanupBase(
    ScanMixin,
    KeyColumnMixin,
    ColumnMixin,
    SqlLineMixin,
):
    # Preserved class-level regex attributes (backwards-compatible).
    CONVERTED_OBTAIN_CALC_PATTERN = CONVERTED_OBTAIN_CALC_PATTERN
    CONVERTED_MODIFY_PATTERN = CONVERTED_MODIFY_PATTERN
    EXEC_SQL_START_PATTERN = EXEC_SQL_START_PATTERN
    EXEC_SQL_END_PATTERN = EXEC_SQL_END_PATTERN
    INCLUDE_PATTERN = INCLUDE_PATTERN
    SQLCODE_IF_PATTERN = SQLCODE_IF_PATTERN
    END_IF_PATTERN = END_IF_PATTERN
    MALFORMED_SQLERROR_ENDIF_PATTERN = MALFORMED_SQLERROR_ENDIF_PATTERN
    MOVE_TO_BARE_FIELD_PATTERN = MOVE_TO_BARE_FIELD_PATTERN
    MOVE_TO_DCL_HOST_PATTERN = MOVE_TO_DCL_HOST_PATTERN
    SQL_LOCATION_PATTERN = SQL_LOCATION_PATTERN
    LINKAGE_SECTION_PATTERN = LINKAGE_SECTION_PATTERN
    TIMESTAMP_PARAGRAPH_PATTERN = TIMESTAMP_PARAGRAPH_PATTERN
    STOP_RUN_PATTERN = STOP_RUN_PATTERN

    # Preserved class-level constant attributes (backwards-compatible).
    PROTECTED_BARE_TARGET_PREFIXES = PROTECTED_BARE_TARGET_PREFIXES
    UPDATE_AUDIT_PREFIXES = UPDATE_AUDIT_PREFIXES
    INSERT_ONLY_AUDIT_PREFIXES = INSERT_ONLY_AUDIT_PREFIXES
    IDENTITY_KEY_PREFIXES = IDENTITY_KEY_PREFIXES

    def __init__(
        self,
        mapping_repository: MappingRepository,
        dclgen_repository: DclgenRepository,
        table_name_resolver: TableNameResolver,
        host_variable_resolver: HostVariableResolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.dclgen_repository = dclgen_repository
        self.table_name_resolver = table_name_resolver
        self.host_variable_resolver = host_variable_resolver
        self.messages: list[str] = []