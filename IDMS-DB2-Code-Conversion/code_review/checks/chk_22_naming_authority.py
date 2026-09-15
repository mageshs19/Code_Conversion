"""CHK-22 DB2 table and column naming authority."""

from __future__ import annotations

import re

from code_review.engine import metadata as meta, sql_blocks as sql
from code_review.engine.check_base import CRITICAL, Check
from code_review.standards import cobol_standards as std

TABLE = re.compile(
    r"\b(?:FROM|UPDATE|INSERT\s+INTO|DELETE\s+FROM)\s+(?P<table>[A-Z0-9_]+)\b"
)
HOST_DOT = re.compile(r":(?P<group>[A-Z0-9-]+)\.(?P<field>[A-Z0-9-]+)")


class NamingAuthorityCheck(Check):
    CHECK_ID = "CHK-22"
    TITLE = "DB2 table and column naming authority"
    SEVERITY = CRITICAL
    ORDER = 220

    def relevant(self, ctx, view) -> bool:
        return view.has_code_token(std.SQL_BLOCK_START)

    def not_relevant_reason(self) -> str:
        return "Program contains no embedded SQL."

    def review(self, ctx, view, record):
        blocks = sql.sql_blocks(view)
        tables = {
            match.group("table")
            for block in blocks
            for match in TABLE.finditer(block.text)
        }

        mapped = meta.mapped_tables(ctx)
        declared = meta.dclgen_tables(ctx)
        authority = mapped | declared

        # ---- 01 every table comes from an authority -----------------
        if not std.ENFORCE_TABLE_AUTHORITY:
            record.skip(
                "01", "Every DB2 table comes from Sheet Mapping or DCLGEN",
                "Not enforced by the site standard.",
            )
        elif not authority:
            record.skip(
                "01", "Every DB2 table comes from Sheet Mapping or DCLGEN",
                "No Sheet Mapping or DCLGEN metadata supplied for this run.",
            )
        else:
            record.expect_all(
                "01", "Every DB2 table comes from Sheet Mapping or DCLGEN",
                sorted(table for table in tables if table not in authority),
            )

        # ---- 02 every table used has a DCLGEN -----------------------
        if not declared:
            record.skip(
                "02", "Every DB2 table used has a DCLGEN",
                "No DCLGEN metadata supplied for this run.",
            )
        else:
            record.expect_all(
                "02", "Every DB2 table used has a DCLGEN",
                sorted(table for table in tables if table not in declared),
            )

        # ---- 03 every column comes from DCLGEN ----------------------
        if not std.ENFORCE_COLUMN_AUTHORITY:
            record.skip(
                "03", "Every DB2 column comes from DCLGEN",
                "Not enforced by the site standard.",
            )
        elif not declared:
            record.skip(
                "03", "Every DB2 column comes from DCLGEN",
                "No DCLGEN metadata supplied for this run.",
            )
        else:
            offenders = []
            for block in blocks:
                match = TABLE.search(block.text)
                if not match:
                    continue
                table = match.group("table")
                available = meta.columns_for_table(ctx, table)
                if not available:
                    continue
                used = {
                    found.group("field").replace("-", "_")
                    for found in HOST_DOT.finditer(block.text)
                }
                bad = sorted(used - available)
                if bad:
                    offenders.append(f"{table}: {', '.join(bad)}")
            record.expect_all(
                "03", "Every DB2 column comes from DCLGEN", offenders,
            )

        # ---- 04 mapped tables resolve to a DCLGEN -------------------
        if not mapped or not declared:
            record.skip(
                "04", "Every Sheet Mapping table used resolves to a DCLGEN",
                "Sheet Mapping or DCLGEN metadata not supplied for this run.",
            )
        else:
            used_mapped = tables & mapped
            record.expect_all(
                "04", "Every Sheet Mapping table used resolves to a DCLGEN",
                sorted(used_mapped - declared),
            )

        # ---- 05 no DCL group without a table ------------------------
        prefix = std.DCLGEN_GROUP_PREFIX.upper()
        groups = {
            match.group("group")
            for block in blocks
            for match in HOST_DOT.finditer(block.text)
        }
        if not declared:
            record.skip(
                "05", f"Every {std.DCLGEN_GROUP_PREFIX} group names a known "
                      f"table",
                "No DCLGEN metadata supplied for this run.",
            )
        else:
            record.expect_all(
                "05", f"Every {std.DCLGEN_GROUP_PREFIX} group names a known "
                      f"table",
                sorted(
                    group for group in groups
                    if group.startswith(prefix)
                    and group[len(prefix):] not in declared
                ),
            )