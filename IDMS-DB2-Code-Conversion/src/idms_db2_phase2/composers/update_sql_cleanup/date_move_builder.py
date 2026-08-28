# LOCATION: src/idms_db2_phase2/composers/update_sql_cleanup/date_move_builder.py
# ACTION: REPLACE ENTIRE FILE

"""
DB2 date move builder (update SQL cleanup).

Builds the COBOL move sequence that converts a CCYYMMDD source value into the
DB2 external date format DD.MM.CCYY before moving it into a DB2 date host
field. Uses the DB2 low-date sentinel (00010101) for null dates.
"""

from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.sql_generation_rules import (
    DATE_COLUMN_PREFIXES,
    DB2_DATE_NULL_SENTINEL,
)


class DateMoveBuilder:
    def is_db2_date_column(self, column_name: str) -> bool:
        column = NameNormalizer.normalize(column_name)
        return any(
            column.startswith(prefix) for prefix in DATE_COLUMN_PREFIXES
        )

    def date_ymd8_to_db2_external_move(
        self,
        source_value: str,
        host_key: str,
        leading: str,
    ) -> list[str]:
        """
        Convert CCYYMMDD into DB2 external date format DD.MM.CCYY.

        Manual standard:
        - Clear DA-CCYYMMDD.
        - Move the source date into DA-CCYYMMDD.
        - If the date is ZERO or SPACES, substitute the DB2 low-date sentinel
          (00010101) instead of moving SPACES to the target.
        - Realign via DA-CCYYMMDD-R -> DA-DD-MM-CCYY.
        """
        source = str(source_value or "").strip()
        indent = leading if leading else "    "

        if not source:
            return [
                f"{indent}MOVE ZEROES TO DA-CCYYMMDD",
                f"{indent}MOVE {DB2_DATE_NULL_SENTINEL} TO DA-CCYYMMDD",
                f"{indent}MOVE CORR DA-CCYYMMDD-R TO DA-DD-MM-CCYY",
                f"{indent}MOVE DA-DD-MM-CCYY TO {host_key}",
            ]

        return [
            f"{indent}MOVE ZEROES TO DA-CCYYMMDD",
            f"{indent}MOVE {source} TO DA-CCYYMMDD",
            f"{indent}IF   DA-CCYYMMDD = ZERO OR DA-CCYYMMDD = SPACES",
            f"{indent}     MOVE {DB2_DATE_NULL_SENTINEL} TO DA-CCYYMMDD",
            f"{indent}END-IF",
            f"{indent}MOVE CORR DA-CCYYMMDD-R TO DA-DD-MM-CCYY",
            f"{indent}MOVE DA-DD-MM-CCYY TO {host_key}",
        ]