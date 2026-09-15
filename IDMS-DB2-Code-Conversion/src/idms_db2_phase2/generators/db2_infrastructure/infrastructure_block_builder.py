# LOCATION: src/idms_db2_phase2/generators/db2_infrastructure/infrastructure_block_builder.py
# ACTION: REPLACE ENTIRE FILE

"""Assembles the generated DB2 infrastructure DATA DIVISION block.

Assembly order only. Every element is rendered by a focused builder:

  1. Infrastructure marker            comment_block
  2. SQLERRWS / SQLCA / DCLGEN        IncludeRenderer
  3. SQL-LOCATION                     SqlLocationBuilder  (off by default)
  4. Cursor end-of-cursor flags       CursorFlagBuilder
  5. Cursor DECLARE statements        CursorDeclareBuilder

CORRECTION - duplicate DZBFARTV include
---------------------------------------
This builder rendered its own include statements as a three-line block,
while the update postprocess rendered a single-line form and scanned for
only that shape. It therefore did not recognise the block already
present and injected DZBFARTV a second time. A duplicated DCLGEN include
duplicates every data-name in the group, which the compiler rejects.

Include emission AND detection now go through IncludeRenderer, so one
shape and one duplicate test serve every caller.

CORRECTION - generated blocks sat in Area A
-------------------------------------------
Lines were emitted with no indent, so after fixed-format sequencing
EXEC SQL and END-EXEC landed at column 8. CHK-06.07 requires column 12.
Indents now come from rules/db2_infrastructure_rules.py.

CORRECTION - duplicate SQL-LOCATION
-----------------------------------
See sql_location_builder.py. SQLERRWS owns the field.

Clean Architecture
------------------
- Section titles and include names: catalogs/output_sections.py
- Indents, tokens and templates:    rules/db2_infrastructure_rules.py
- No regex here.
- No program, record, table, cursor or host variable name hardcoded.
"""

from __future__ import annotations

from catalogs.output_sections import (
    DB2_CURSOR_DECLARATIONS_MARKER,
    DB2_CURSOR_FLAGS_MARKER,
    DB2_INFRASTRUCTURE_MARKER,
    SQLCA_INCLUDE_NAME,
    SQLERRWS_INCLUDE_NAME,
)
from idms_db2_phase2.generators.db2_infrastructure.cursor_declare_builder import (
    CursorDeclareBuilder,
)
from idms_db2_phase2.generators.db2_infrastructure.cursor_flag_builder import (
    CursorFlagBuilder,
)
from idms_db2_phase2.generators.db2_infrastructure.cursor_spec import CursorSpec
from idms_db2_phase2.generators.db2_infrastructure.include_renderer import (
    IncludeRenderer,
)
from idms_db2_phase2.generators.db2_infrastructure.sql_location_builder import (
    SqlLocationBuilder,
)


class InfrastructureBlockBuilder:
    """Assembles the DB2 infrastructure block for WORKING-STORAGE."""

    def __init__(self, line_utils) -> None:
        self.line_utils = line_utils
        self.includes = IncludeRenderer(line_utils)
        self.sql_location = SqlLocationBuilder(line_utils)
        self.flags = CursorFlagBuilder()
        self.declares = CursorDeclareBuilder(line_utils)

    # =================================================================
    # Public entry point
    # =================================================================
    def build(
        self,
        include_names: list[str],
        cursor_specs: list[dict[str, object]],
    ) -> str:
        specs = CursorSpec.read_all(cursor_specs)

        lines: list[str] = []
        lines.extend(self._infrastructure_section(include_names))
        lines.extend(self.sql_location.build())

        if specs:
            lines.extend(self._flags_section(specs))
            lines.extend(self._declarations_section(specs))

        return "\n".join(lines).rstrip() + "\n"

    # =================================================================
    # Sections
    # =================================================================
    def _infrastructure_section(self, include_names: list[str]) -> list[str]:
        """Marker comment, then SQLERRWS, SQLCA and each DCLGEN include.

        SQLERRWS leads because it declares SQL-LOCATION, which every
        generated paragraph moves into before issuing SQL.
        """
        return [
            *self.line_utils.comment_block(DB2_INFRASTRUCTURE_MARKER),
            *self.includes.render_all(
                [
                    SQLERRWS_INCLUDE_NAME,
                    SQLCA_INCLUDE_NAME,
                    *(include_names or []),
                ]
            ),
        ]

    def _flags_section(self, specs: list[CursorSpec]) -> list[str]:
        return [
            "",
            *self.line_utils.comment_block(DB2_CURSOR_FLAGS_MARKER),
            *self.flags.build(specs),
        ]

    def _declarations_section(self, specs: list[CursorSpec]) -> list[str]:
        lines: list[str] = [
            "",
            *self.line_utils.comment_block(DB2_CURSOR_DECLARATIONS_MARKER),
        ]

        for spec in specs:
            lines.extend(self.declares.build(spec))
            lines.append("")

        return lines