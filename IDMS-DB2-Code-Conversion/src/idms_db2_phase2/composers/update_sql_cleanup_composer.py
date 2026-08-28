# LOCATION: src/idms_db2_phase2/composers/update_sql_cleanup_composer.py
# ACTION: CREATE NEW FILE (this replaces update_program_sql_feedback_composer.py)

"""
Update SQL cleanup composer.

Fixes update-program SQL issues:
- malformed PERFORM SQLERROR.END-IF.
- bare changed field move before MODIFY.
- unnecessary OBTAIN CALC SELECT.
- broad MODIFY UPDATE / WHERE (rewritten to changed field + audit fields).

Composite key WHERE includes all PK / CALC key fields; FK / FOREIGN columns
are never used in WHERE. No program, table, DCLGEN group, or field name is
hardcoded. Sheet Mapping decides table/column mapping; DCLGEN decides host
variable spelling. Delegates each pass to a focused helper class.
"""

from __future__ import annotations

import re

from idms_db2_phase2.composers.update_sql_cleanup.bare_move_rewriter import (
    BareMoveRewriter,
)
from idms_db2_phase2.composers.update_sql_cleanup.composer_patterns import (
    ANY_DCL_DOT_REFERENCE_PATTERN,
    ANY_DCL_OF_REFERENCE_PATTERN,
    DATE_COLUMN_PREFIXES,
    MOVE_TO_DCL_DOT_HOST_PATTERN,
    STRING_INTO_DCL_DOT_HOST_PATTERN,
    STRING_INTO_DCL_HOST_PATTERN,
)
from idms_db2_phase2.composers.update_sql_cleanup.date_move_builder import (
    DateMoveBuilder,
)
from idms_db2_phase2.composers.update_sql_cleanup.modify_update_rewriter import (
    ModifyUpdateRewriter,
)
from idms_db2_phase2.composers.update_sql_cleanup.obtain_calc_remover import (
    ObtainCalcRemover,
)
from idms_db2_phase2.composers.update_sql_cleanup.sql_block_scanner import (
    SqlBlockScanner,
)
from idms_db2_phase2.composers.update_sql_cleanup.sqlerror_normalizer import (
    SqlerrorNormalizer,
)
from idms_db2_phase2.composers.update_sql_cleanup_base import (
    UpdateSqlCleanupBase,
)
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class UpdateSqlCleanupComposer(UpdateSqlCleanupBase):
    # Composer-specific patterns exposed for helpers that read them via owner.
    MOVE_TO_DCL_DOT_HOST_PATTERN = MOVE_TO_DCL_DOT_HOST_PATTERN
    STRING_INTO_DCL_HOST_PATTERN = STRING_INTO_DCL_HOST_PATTERN
    STRING_INTO_DCL_DOT_HOST_PATTERN = STRING_INTO_DCL_DOT_HOST_PATTERN
    ANY_DCL_OF_REFERENCE_PATTERN = ANY_DCL_OF_REFERENCE_PATTERN
    ANY_DCL_DOT_REFERENCE_PATTERN = ANY_DCL_DOT_REFERENCE_PATTERN
    DATE_COLUMN_PREFIXES = DATE_COLUMN_PREFIXES

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._scanner = SqlBlockScanner(self)
        self._date_builder = DateMoveBuilder()
        self._sqlerror = SqlerrorNormalizer(self)
        self._bare_move = BareMoveRewriter(
            owner=self,
            scanner=self._scanner,
            date_builder=self._date_builder,
        )
        self._obtain_calc = ObtainCalcRemover(self, self._scanner)
        self._modify_update = ModifyUpdateRewriter(self, self._scanner)

    def compose(self, text: str) -> str:
        self.messages = []
        output = str(text or "")

        if not output.strip():
            return output

        output = self._sqlerror.normalize(output)
        output = self._bare_move.rewrite(output)
        output = self._obtain_calc.rewrite(output)
        output = self._modify_update.rewrite(output)

        return output.rstrip() + "\n"

    def _db2_primary_key_columns(
        self,
        record: str,
        table: str,
    ) -> list[str]:
        """
        Composite PK / CALC key columns for WHERE.

        - Include all DB2 PRIMARY / KEY columns.
        - Include all IDMS CALC key columns.
        - Exclude FK / FOREIGN / relationship columns.
        - Preserve mapping order.
        """
        output: list[str] = []
        seen: set[str] = set()

        for row in self.mapping_repository.rows_for_record(record):
            idms_key = NameNormalizer.normalize(getattr(row, "idms_key", ""))
            db2_key = NameNormalizer.normalize(getattr(row, "db2_key", ""))
            relation = NameNormalizer.normalize(getattr(row, "relation", ""))
            column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
                or getattr(row, "cross_application_db2_field_name", "")
            )
            if not column:
                continue

            combined_text = " ".join([idms_key, db2_key, relation])
            padded_text = f" {combined_text} "

            if "FOREIGN" in combined_text:
                continue
            if " FK " in padded_text:
                continue

            is_key_column = (
                "PRIMARY" in db2_key
                or db2_key == "KEY"
                or "PRIMARY" in idms_key
                or idms_key == "KEY"
                or "CALC" in idms_key
            )
            if not is_key_column:
                continue
            if column in seen:
                continue

            seen.add(column)
            output.append(column)

        return self._filter_existing_dclgen_columns(table, output)