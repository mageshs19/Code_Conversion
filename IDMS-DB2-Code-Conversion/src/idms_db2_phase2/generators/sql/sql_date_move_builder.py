# LOCATION: src/idms_db2_phase2/generators/sql/sql_date_move_builder.py
# ACTION: REPLACE ENTIRE FILE

"""DB2 date column detection and CCYYMMDD -> DD.MM.CCYY move builder."""

from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.sql_generation_rules import (
    DATE_COLUMN_PREFIXES,
    DATE_STAGING_FIELDS,
    DB2_DATE_NULL_SENTINEL,
)


class SqlDateMoveBuilder:

    def is_db2_date_column(self, column_name: str) -> bool:
        column = NameNormalizer.normalize(column_name)
        return any(
            column.startswith(prefix) for prefix in DATE_COLUMN_PREFIXES
        )

    @staticmethod
    def _is_staging_field(source: str) -> bool:
        """True when the source is already a DB2 date staging field.

        A staging field is this builder's OUTPUT, not a valid input. Passing
        DA-DD-MM-CCYY back in moves 10 bytes into an 8-byte group, truncating
        the year, and the CORR move back writes garbage into the DB2 host.
        """
        return str(source or "").strip().upper() in DATE_STAGING_FIELDS

    def date_ymd8_to_db2_external_move(
        self,
        source_value: str,
        host_key: str,
    ) -> list[str]:
        """Convert a CCYYMMDD source value into DB2 external date DD.MM.CCYY,
        then move it into the DB2 date host field.

        Manual standard:
        - Clear DA-CCYYMMDD.
        - Move the source date into DA-CCYYMMDD.
        - If the date is ZERO or SPACES, substitute the DB2 low-date sentinel
          (00010101) instead of moving SPACES to the target.
        - Realign via DA-CCYYMMDD-R -> DA-DD-MM-CCYY.

        Precondition: source_value must be a CCYYMMDD (8-position) field.
        A staging field is rejected by _is_staging_field and moved directly,
        because it is already in DB2 external form.
        """
        source = str(source_value or "").strip()

        # Already converted. Re-running the block would destroy the value.
        if self._is_staging_field(source):
            return [
                f"MOVE DA-DD-MM-CCYY TO {host_key}",
            ]

        if not source:
            return [
                "MOVE ZEROES TO DA-CCYYMMDD",
                f"MOVE {DB2_DATE_NULL_SENTINEL} TO DA-CCYYMMDD",
                "MOVE CORR DA-CCYYMMDD-R TO DA-DD-MM-CCYY",
                f"MOVE DA-DD-MM-CCYY TO {host_key}",
            ]

        return [
            "MOVE ZEROES TO DA-CCYYMMDD",
            f"MOVE {source} TO DA-CCYYMMDD",
            "IF DA-CCYYMMDD = ZERO OR DA-CCYYMMDD = SPACES",
            f"    MOVE {DB2_DATE_NULL_SENTINEL} TO DA-CCYYMMDD",
            "END-IF",
            "MOVE CORR DA-CCYYMMDD-R TO DA-DD-MM-CCYY",
            f"MOVE DA-DD-MM-CCYY TO {host_key}",
        ]