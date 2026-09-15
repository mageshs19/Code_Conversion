# LOCATION: src/idms_db2_phase2/generators/db2_infrastructure/sql_location_builder.py
# ACTION: CREATE NEW FILE

"""Builds the SQL-LOCATION declaration, when the site wants one.

CORRECTION - duplicate data-name
--------------------------------
The infrastructure block unconditionally emitted

    01  SQL-LOCATION                   PIC X(40) VALUE SPACES.

while also emitting EXEC SQL INCLUDE SQLERRWS. SQLERRWS already declares
SQL-LOCATION, so the program carried a duplicate data-name and the
compiler rejected it.

The COBOL team's manual reference program has no local declaration: it
moves into the field and lets the copybook own it. Emission is therefore
off by default, controlled by
catalogs.output_sections.DECLARE_SQL_LOCATION_FIELD.
"""

from __future__ import annotations

from catalogs.output_sections import (
    DB2_SQL_ERROR_LOCATION_MARKER,
    DECLARE_SQL_LOCATION_FIELD,
    SQL_LOCATION_FIELD_NAME,
    SQL_LOCATION_PICTURE,
)
from rules.db2_infrastructure_rules import SQL_LOCATION_DECLARATION_TEMPLATE


class SqlLocationBuilder:
    """Renders the SQL-LOCATION block, or nothing at all."""

    def __init__(self, line_utils) -> None:
        self.line_utils = line_utils

    def build(self) -> list[str]:
        if not DECLARE_SQL_LOCATION_FIELD:
            return []

        return [
            "",
            *self.line_utils.comment_block(DB2_SQL_ERROR_LOCATION_MARKER),
            SQL_LOCATION_DECLARATION_TEMPLATE.format(
                name=SQL_LOCATION_FIELD_NAME,
                picture=SQL_LOCATION_PICTURE,
            ),
        ]