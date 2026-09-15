"""CHK-18 Audit column and date handling."""

from __future__ import annotations

import re

from code_review.engine import metadata as meta, sql_blocks as sql
from code_review.engine.check_base import MAJOR, UPDATE, Check
from code_review.standards import cobol_standards as std

UPDATE_TABLE = re.compile(r"\bUPDATE\s+(?P<table>[A-Z0-9_]+)\b")
SET_CLAUSE = re.compile(r"\bSET\b(?P<body>.*?)\bWHERE\b")
ASSIGNMENT = re.compile(r"(?P<column>[A-Z][A-Z0-9_]*)\s*=")
MOVE_TO = re.compile(r"^MOVE\s+(?P<source>.+?)\s+TO\s+(?P<target>.+?)\.?$")


class AuditAndDateHandlingCheck(Check):
    CHECK_ID = "CHK-18"
    TITLE = "Audit column and date handling"
    SEVERITY = MAJOR
    APPLIES_TO = UPDATE
    ORDER = 180

    def relevant(self, ctx, view) -> bool:
        return any(b.verb == "UPDATE" for b in sql.sql_blocks(view))

    def not_relevant_reason(self) -> str:
        return "Program issues no UPDATE statement."

    def review(self, ctx, view, record):
        updates = [b for b in sql.sql_blocks(view) if b.verb == "UPDATE"]
        plans = [(b, self._table(b), self._set_columns(b)) for b in updates]

        # ---- 01 update audit columns are set ------------------------
        if not meta.dclgen_tables(ctx):
            record.skip(
                "01", "Every UPDATE sets its update audit columns",
                "No DCLGEN metadata supplied for this run.",
            )
        else:
            offenders = []
            for block, table, columns in plans:
                expected = meta.columns_with_prefix(
                    ctx, table, std.UPDATE_AUDIT_PREFIXES,
                )
                missing = sorted(expected - set(columns))
                if expected and missing:
                    offenders.append(f"{table}: {', '.join(missing)}")
            record.expect_all(
                "01", "Every UPDATE sets its update audit columns", offenders,
            )

        # ---- 02 insert-only audit columns stay out ------------------
        offenders = []
        for block, table, columns in plans:
            bad = [
                column for column in columns
                if column.startswith(std.INSERT_ONLY_AUDIT_PREFIXES)
            ]
            if bad:
                offenders.append(f"{table}: {', '.join(bad)}")
        record.expect_all(
            "02",
            f"No UPDATE sets {', '.join(std.INSERT_ONLY_AUDIT_PREFIXES)}",
            offenders,
        )

        # ---- 03 audit host moves precede the UPDATE -----------------
        if not std.ENFORCE_AUDIT_MOVES_BEFORE_UPDATE:
            record.skip(
                "03", "Audit host moves precede each UPDATE",
                "Not enforced by the site standard.",
            )
        elif not meta.dclgen_tables(ctx):
            record.skip(
                "03", "Audit host moves precede each UPDATE",
                "No DCLGEN metadata supplied for this run.",
            )
        else:
            offenders = []
            for block, table, _columns in plans:
                expected = meta.columns_with_prefix(
                    ctx, table, std.UPDATE_AUDIT_PREFIXES,
                )
                if not expected:
                    continue
                hosts = meta.hosts_for_table(ctx, table)
                wanted = {
                    hosts[column] for column in expected if column in hosts
                }
                if not wanted:
                    continue
                window = " ".join(
                    sql.lines_before(view, block, std.AUDIT_MOVE_LOOKBACK)
                )
                missing = sorted(
                    host for host in wanted if host not in window
                )
                if missing:
                    offenders.append(f"{table}: {', '.join(missing)}")
            record.expect_all(
                "03", "Audit host moves precede each UPDATE", offenders,
            )

        # ---- 04 date staging fields are used ------------------------
        if not std.ENFORCE_DATE_STAGING:
            record.skip(
                "04", "Date values pass through the staging fields",
                "Not enforced by the site standard.",
            )
        else:
            date_hosts = self._date_hosts(ctx)
            if not date_hosts:
                record.skip(
                    "04", "Date values pass through the staging fields",
                    "No DCLGEN date column supplied for this run.",
                )
            else:
                offenders = [
                    line for line in view.code
                    if self._raw_date_move(line, date_hosts)
                ]
                record.expect_none(
                    "04", "Date values pass through the staging fields",
                    offenders,
                )

        # ---- 05 date sentinel is declared ---------------------------
        date_hosts = self._date_hosts(ctx)
        if not date_hosts:
            record.skip(
                "05", f"DB2 date sentinel {std.DB2_DATE_SENTINEL} is used",
                "No DCLGEN date column supplied for this run.",
            )
        else:
            record.expect(
                "05", f"DB2 date sentinel {std.DB2_DATE_SENTINEL} is used",
                view.has_code_token(std.DB2_DATE_SENTINEL),
                note="Sentinel not found. Empty source dates may move "
                     "SPACES into a DB2 date column.",
            )

        # ---- 06 timestamp source field is used ----------------------
        if not any(
            meta.columns_with_prefix(ctx, table, ("TS_UPDATE",))
            for _block, table, _columns in plans
        ):
            record.skip(
                "06", f"Update timestamps come from "
                      f"{std.TIMESTAMP_SOURCE_FIELD}",
                "No TS_UPDATE column supplied for this run.",
            )
        else:
            record.expect(
                "06", f"Update timestamps come from "
                      f"{std.TIMESTAMP_SOURCE_FIELD}",
                view.has_code_token(std.TIMESTAMP_SOURCE_FIELD),
                note=f"{std.TIMESTAMP_SOURCE_FIELD} not referenced.",
            )

    # ---- helpers ----------------------------------------------------
    @staticmethod
    def _table(block) -> str:
        match = UPDATE_TABLE.search(block.text)
        return match.group("table") if match else ""

    @staticmethod
    def _set_columns(block) -> list[str]:
        match = SET_CLAUSE.search(block.text)
        if not match:
            return []
        return [
            found.group("column")
            for found in ASSIGNMENT.finditer(match.group("body"))
        ]

    @staticmethod
    def _date_hosts(ctx) -> set[str]:
        out: set[str] = set()
        for table in meta.dclgen_tables(ctx):
            columns = meta.columns_with_prefix(
                ctx, table, std.DATE_COLUMN_PREFIXES,
            )
            hosts = meta.hosts_for_table(ctx, table)
            out.update(
                hosts[column] for column in columns if column in hosts
            )
        return out

    @staticmethod
    def _raw_date_move(line, date_hosts: set[str]) -> bool:
        """A MOVE into a DB2 date host that bypasses the staging fields."""
        match = MOVE_TO.match(sql.norm(line.logical))
        if not match:
            return False
        target = match.group("target")
        if not any(host in target for host in date_hosts):
            return False
        source = match.group("source")
        if any(field in source for field in std.DATE_STAGING_FIELDS):
            return False
        return std.TIMESTAMP_SOURCE_FIELD not in source