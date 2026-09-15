"""CHK-17 Update WHERE key integrity."""

from __future__ import annotations

import re

from code_review.engine import metadata as meta, sql_blocks as sql
from code_review.engine.check_base import CRITICAL, UPDATE, Check
from code_review.standards import cobol_standards as std

WHERE_CLAUSE = re.compile(r"\bWHERE\b(?P<body>.*?)(?:\bQUERYNO\b|$)")
COMPARISON = re.compile(r"(?P<column>[A-Z][A-Z0-9_]*)\s*=\s*(?P<value>\S+)")
TARGET = re.compile(
    r"\b(?:UPDATE|DELETE\s+FROM)\s+(?P<table>[A-Z0-9_]+)\b"
)


class UpdateWhereKeyIntegrityCheck(Check):
    CHECK_ID = "CHK-17"
    TITLE = "Update WHERE key integrity"
    SEVERITY = CRITICAL
    APPLIES_TO = UPDATE
    ORDER = 170

    def relevant(self, ctx, view) -> bool:
        return any(
            b.verb in ("UPDATE", "DELETE")
            and not sql.targets_restart(b, std.RESTART_TABLE_NAME_HINTS)
            for b in sql.sql_blocks(view)
        )

    def not_relevant_reason(self) -> str:
        return "Program issues no business UPDATE or DELETE statement."

    def review(self, ctx, view, record):
        # Restart writes are keyed on restart-table columns that are not
        # business records in Sheet Mapping. CHK-20 owns them.
        blocks = [
            b for b in sql.sql_blocks(view)
            if b.verb in ("UPDATE", "DELETE")
            and not sql.targets_restart(b, std.RESTART_TABLE_NAME_HINTS)
        ]
        plans = [
            (b, self._where_columns(b), self._where_body(b)) for b in blocks
        ]

        keys_by_record = self._keys_by_record(ctx)
        all_keys = set().union(*keys_by_record.values()) if keys_by_record else set()
        foreign = meta.all_foreign_key_columns(ctx)

        # ---- 01 every write is key qualified ------------------------
        record.expect_none(
            "01", "Every business UPDATE and DELETE has a WHERE clause",
            [block for block, _columns, body in plans if not body],
        )

        # ---- 02 WHERE references a key-style column -----------------
        if not all_keys:
            record.skip(
                "02", "Every WHERE references a primary key column",
                "No Sheet Mapping key metadata supplied for this run.",
            )
        else:
            record.expect_none(
                "02", "Every WHERE references a primary key column",
                [
                    block for block, columns, body in plans
                    if body and not (set(columns) & all_keys)
                ],
            )

        # ---- 03 composite keys are complete -------------------------
        #
        # Keys are evaluated per record, not pooled. Several IDMS records
        # can map to one DB2 table, each with its own composite key, so a
        # pooled set would demand columns from an unrelated record.
        if not keys_by_record:
            record.skip(
                "03", "Composite keys appear in full",
                "No Sheet Mapping key metadata supplied for this run.",
            )
        else:
            record.expect_all(
                "03", "Composite keys appear in full",
                self._incomplete_keys(plans, keys_by_record),
            )

        # ---- 04 no foreign key in WHERE -----------------------------
        if not std.ENFORCE_WHERE_NO_FOREIGN_KEY:
            record.skip(
                "04", "No WHERE uses a foreign key column",
                "Not enforced by the site standard.",
            )
        elif not foreign:
            record.skip(
                "04", "No WHERE uses a foreign key column",
                "No Sheet Mapping relationship metadata supplied for "
                "this run.",
            )
        else:
            offenders = []
            for block, columns, _body in plans:
                bad = sorted(set(columns) & foreign)
                if bad:
                    offenders.append(
                        f"line {block.line_number}: {', '.join(bad)}"
                    )
            record.expect_all(
                "04", "No WHERE uses a foreign key column", offenders,
            )

        # ---- 05 comparisons use host variables ----------------------
        if not std.ENFORCE_WHERE_HOST_VARIABLES:
            record.skip(
                "05", "Every WHERE comparison uses a host variable",
                "Not enforced by the site standard.",
            )
        else:
            offenders = []
            for block, _columns, body in plans:
                if not body:
                    continue
                literals = [
                    found.group(0)
                    for found in COMPARISON.finditer(body)
                    if std.HOST_REFERENCE_MARKER not in found.group("value")
                ]
                if literals:
                    offenders.append(
                        f"line {block.line_number}: {', '.join(literals[:3])}"
                    )
            record.expect_all(
                "05", "Every WHERE comparison uses a host variable",
                offenders,
            )

        # ---- 06 no always-true predicate ----------------------------
        record.expect_none(
            "06", "No WHERE uses an always-true predicate",
            [
                block for block, _columns, body in plans
                if any(
                    predicate in body
                    for predicate in std.FORBIDDEN_WHERE_PREDICATES
                )
            ],
        )

    # ---- helpers ----------------------------------------------------
    @staticmethod
    def _keys_by_record(ctx) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for name in meta.mapped_records(ctx):
            columns = set(
                meta.primary_key_columns(ctx, name, std.KEY_TEXT_MARKERS)
            )
            if columns:
                out[name] = columns
        return out

    @classmethod
    def _incomplete_keys(cls, plans, keys_by_record) -> list[str]:
        out: list[str] = []
        for block, columns, body in plans:
            if not body:
                continue
            used = set(columns)
            candidates = [
                (name, keys)
                for name, keys in keys_by_record.items()
                if keys & used
            ]
            if not candidates:
                continue
            if any(keys <= used for _name, keys in candidates):
                continue
            name, keys = max(
                candidates, key=lambda item: len(item[1] & used)
            )
            missing = sorted(keys - used)
            out.append(
                f"{cls._table(block)} line {block.line_number} "
                f"for record {name} missing {', '.join(missing)}"
            )
        return out

    @staticmethod
    def _where_body(block) -> str:
        match = WHERE_CLAUSE.search(block.text)
        return match.group("body").strip() if match else ""

    @classmethod
    def _where_columns(cls, block) -> list[str]:
        body = cls._where_body(block)
        return [
            found.group("column") for found in COMPARISON.finditer(body)
        ]

    @staticmethod
    def _table(block) -> str:
        match = TARGET.search(block.text)
        return match.group("table") if match else ""