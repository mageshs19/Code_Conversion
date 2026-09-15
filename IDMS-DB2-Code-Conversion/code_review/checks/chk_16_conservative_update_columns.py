"""CHK-16 Conservative update column selection."""

from __future__ import annotations

import re

from code_review.engine import metadata as meta, sql_blocks as sql
from code_review.engine.check_base import CRITICAL, UPDATE, Check
from code_review.standards import cobol_standards as std

UPDATE_TABLE = re.compile(r"\bUPDATE\s+(?P<table>[A-Z0-9_]+)\b")
SET_CLAUSE = re.compile(r"\bSET\b(?P<body>.*?)\bWHERE\b")
ASSIGNMENT = re.compile(r"(?P<column>[A-Z][A-Z0-9_]*)\s*=")


class ConservativeUpdateColumnsCheck(Check):
    CHECK_ID = "CHK-16"
    TITLE = "Conservative update column selection"
    SEVERITY = CRITICAL
    APPLIES_TO = UPDATE
    ORDER = 160

    def relevant(self, ctx, view) -> bool:
        return any(b.verb == "UPDATE" for b in sql.sql_blocks(view))

    def not_relevant_reason(self) -> str:
        return "Program issues no UPDATE statement."

    def review(self, ctx, view, record):
        updates = [b for b in sql.sql_blocks(view) if b.verb == "UPDATE"]
        plans = [(b, self._table(b), self._set_columns(b)) for b in updates]

        # ---- 01 every UPDATE sets at least one column ---------------
        record.expect_none(
            "01", "Every UPDATE sets at least one column",
            [block for block, _table, columns in plans if not columns],
        )

        # ---- 02 no insert-only audit column in SET ------------------
        offenders = []
        for block, _table, columns in plans:
            bad = [
                column for column in columns
                if column.startswith(std.INSERT_ONLY_AUDIT_PREFIXES)
            ]
            if bad:
                offenders.append(f"{block.line_number}: {', '.join(bad)}")
        record.expect_all(
            "02",
            f"No UPDATE sets an insert-only audit column "
            f"{std.INSERT_ONLY_AUDIT_PREFIXES}",
            offenders,
        )

        # ---- 03 key columns stay out of SET -------------------------
        keys = meta.all_primary_key_columns(ctx, std.KEY_TEXT_MARKERS)
        if not keys:
            record.skip(
                "03", "No UPDATE sets a primary key column",
                "No Sheet Mapping key metadata supplied for this run.",
            )
        else:
            offenders = []
            for block, _table, columns in plans:
                bad = sorted(set(columns) & keys)
                if bad:
                    offenders.append(
                        f"{block.line_number}: {', '.join(bad)}"
                    )
            record.expect_all(
                "03", "No UPDATE sets a primary key column", offenders,
            )

        # ---- 04 the update is not broad -----------------------------
        if not std.ENFORCE_CONSERVATIVE_UPDATE:
            record.skip(
                "04", "No UPDATE rewrites the whole row",
                "Not enforced by the site standard.",
            )
        elif not meta.dclgen_tables(ctx):
            record.skip(
                "04", "No UPDATE rewrites the whole row",
                "No DCLGEN metadata supplied for this run.",
            )
        else:
            offenders = []
            for block, table, columns in plans:
                available = meta.columns_for_table(ctx, table)
                if not available or not columns:
                    continue
                ratio = len(set(columns) & available) / len(available)
                if ratio >= std.BROAD_UPDATE_RATIO:
                    offenders.append(
                        f"{table} sets {len(columns)} of {len(available)} "
                        f"columns"
                    )
            record.expect_all(
                "04", "No UPDATE rewrites the whole row", offenders,
            )

        # ---- 05 every SET column exists in DCLGEN -------------------
        if not meta.dclgen_tables(ctx):
            record.skip(
                "05", "Every updated column exists in DCLGEN",
                "No DCLGEN metadata supplied for this run.",
            )
        else:
            offenders = []
            for block, table, columns in plans:
                available = meta.columns_for_table(ctx, table)
                if not available:
                    continue
                bad = sorted(set(columns) - available)
                if bad:
                    offenders.append(f"{table}: {', '.join(bad)}")
            record.expect_all(
                "05", "Every updated column exists in DCLGEN", offenders,
            )

        # ---- 06 no incomplete-metadata marker remains ---------------
        record.expect_none(
            "06", "No update was skipped for incomplete metadata",
            [
                line for line in view.comments
                if any(m in line.logical for m in std.MISSING_MAPPING_MARKERS)
            ],
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