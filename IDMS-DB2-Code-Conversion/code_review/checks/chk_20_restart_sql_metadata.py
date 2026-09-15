"""CHK-20 Restart SQL generated from DCLGEN metadata."""

from __future__ import annotations

import re

from code_review.engine import metadata as meta, sql_blocks as sql
from code_review.engine.check_base import MAJOR, UPDATE, Check
from code_review.standards import cobol_standards as std

TABLE = re.compile(
    r"\b(?:FROM|UPDATE|INSERT\s+INTO)\s+(?P<table>[A-Z0-9_]+)\b"
)
HOST_DOT = re.compile(r":(?P<group>[A-Z0-9-]+)\.(?P<field>[A-Z0-9-]+)")


class RestartSqlMetadataCheck(Check):
    CHECK_ID = "CHK-20"
    TITLE = "Restart SQL generated from DCLGEN metadata"
    SEVERITY = MAJOR
    APPLIES_TO = UPDATE
    ORDER = 200

    def relevant(self, ctx, view) -> bool:
        return bool(self._restart_blocks(view))

    def not_relevant_reason(self) -> str:
        return (
            "No restart SQL generated. The legacy IDMS restart flow is "
            "preserved, pending Sheet Mapping input (decision D-3)."
        )

    def review(self, ctx, view, record):
        blocks = self._restart_blocks(view)
        tables = {self._table(b) for b in blocks} - {""}

        # ---- 01 restart SQL targets one table -----------------------
        record.expect(
            "01", "Restart SQL targets a single restart table",
            len(tables) == 1,
            note=f"tables: {', '.join(sorted(tables)) or 'none'}",
        )

        # ---- 02 the table is a recognisable restart table -----------
        record.expect_all(
            "02", f"The restart table name carries a "
                  f"{' or '.join(std.RESTART_TABLE_NAME_HINTS)} marker",
            sorted(
                table for table in tables
                if not any(
                    hint in table for hint in std.RESTART_TABLE_NAME_HINTS
                )
            ),
        )

        # ---- 03 the table exists in DCLGEN --------------------------
        known = meta.dclgen_tables(ctx)
        if not known:
            record.skip(
                "03", "The restart table exists in DCLGEN",
                "No DCLGEN metadata supplied for this run.",
            )
        else:
            record.expect_all(
                "03", "The restart table exists in DCLGEN",
                sorted(table for table in tables if table not in known),
            )

        # ---- 04 every restart column exists in DCLGEN ---------------
        if not known:
            record.skip(
                "04", "Every restart column exists in DCLGEN",
                "No DCLGEN metadata supplied for this run.",
            )
        else:
            offenders = []
            for block in blocks:
                table = self._table(block)
                available = meta.columns_for_table(ctx, table)
                if not available:
                    continue
                bad = sorted(self._columns(block) - available)
                if bad:
                    offenders.append(f"{table}: {', '.join(bad)}")
            record.expect_all(
                "04", "Every restart column exists in DCLGEN", offenders,
            )

        # ---- 05 host references use a DCLGEN group ------------------
        prefix = std.DCLGEN_GROUP_PREFIX.upper()
        offenders = []
        for block in blocks:
            for match in HOST_DOT.finditer(block.text):
                group = match.group("group")
                if not group.startswith(prefix):
                    offenders.append(f"{group}.{match.group('field')}")
        record.expect_all(
            "05", f"Every restart host reference uses a "
                  f"{std.DCLGEN_GROUP_PREFIX} group",
            sorted(set(offenders)),
        )

        # ---- 06 QUERYNO ---------------------------------------------
        if not std.ENFORCE_RESTART_QUERYNO:
            record.skip(
                "06", "Every restart statement carries its QUERYNO",
                "Restart QUERYNO values conflict between "
                "update_postprocess_rules and update_restart_rules "
                "(decision D-3).",
            )
        else:
            expected = {
                "SELECT": std.RESTART_SELECT_QUERYNO,
                "UPDATE": std.RESTART_UPDATE_QUERYNO,
                "INSERT": std.RESTART_INSERT_QUERYNO,
            }
            offenders = []
            for block in blocks:
                wanted = expected.get(block.verb, "")
                if not wanted:
                    continue
                if f"QUERYNO {wanted}" not in block.text:
                    offenders.append(
                        f"{block.verb} at line {block.line_number}"
                    )
            record.expect_all(
                "06", "Every restart statement carries its QUERYNO",
                offenders,
            )

        # ---- 07 SQL-LOCATION before each restart statement ----------
        #
        # Without this, a restart SQL failure reports whatever location the
        # previous business statement left in SQL-LOCATION, sending the
        # operator to the wrong paragraph.
        if not std.ENFORCE_SQL_LOCATION_BEFORE_SQL:
            record.skip(
                "07", f"{std.SQL_LOCATION_FIELD} is set before each restart "
                      f"statement",
                "Not enforced by the site standard.",
            )
        else:
            record.expect_none(
                "07", f"{std.SQL_LOCATION_FIELD} is set before each restart "
                      f"statement",
                [
                    b for b in blocks
                    if not self._location_set_before(view, b)
                ],
            )

    # ---- helpers ----------------------------------------------------
    @classmethod
    def _restart_blocks(cls, view) -> list:
        return [
            block for block in sql.sql_blocks(view)
            if block.verb in std.RESTART_SQL_OPERATIONS
            and sql.targets_restart(block, std.RESTART_TABLE_NAME_HINTS)
        ]

    @staticmethod
    def _table(block) -> str:
        match = TABLE.search(block.text)
        return match.group("table") if match else ""

    @staticmethod
    def _columns(block) -> set[str]:
        return {
            match.group("field").replace("-", "_")
            for match in HOST_DOT.finditer(block.text)
        }

    @staticmethod
    def _location_set_before(view, block) -> bool:
        window = sql.lines_before(view, block, std.SQL_LOCATION_LOOKBACK)
        return any(
            line.startswith(std.SQL_LOCATION_MOVE_PREFIX)
            and std.SQL_LOCATION_MOVE_SUFFIX in line
            for line in window
        )