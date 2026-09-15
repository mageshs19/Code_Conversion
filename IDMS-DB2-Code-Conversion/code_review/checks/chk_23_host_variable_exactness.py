"""CHK-23 DCLGEN host variable name exactness."""

from __future__ import annotations

import re

from code_review.engine import metadata as meta, sql_blocks as sql
from code_review.engine.check_base import CRITICAL, Check
from code_review.standards import cobol_standards as std

HOST_DOT = re.compile(r":(?P<group>[A-Z0-9-]+)\.(?P<field>[A-Z0-9-]+)")
QUALIFIED = re.compile(
    r"\b(?P<field>[A-Z][A-Z0-9-]*)\s+(?:OF|IN)\s+(?P<group>[A-Z][A-Z0-9-]*)\b"
)


class HostVariableExactnessCheck(Check):
    CHECK_ID = "CHK-23"
    TITLE = "DCLGEN host variable name exactness"
    SEVERITY = CRITICAL
    ORDER = 230

    def relevant(self, ctx, view) -> bool:
        return bool(meta.dclgen_tables(ctx))

    def not_relevant_reason(self) -> str:
        return "No DCLGEN metadata supplied for this run."

    def review(self, ctx, view, record):
        prefix = std.DCLGEN_GROUP_PREFIX.upper()
        known_hosts = self._all_hosts(ctx)
        group_hosts = self._hosts_by_group(ctx)

        sql_refs = self._sql_references(view)
        cobol_refs = self._cobol_references(view, prefix)

        # ---- 01 SQL host names exist in DCLGEN ----------------------
        if not std.ENFORCE_HOST_NAME_EXACTNESS:
            record.skip(
                "01", "Every SQL host variable exists in DCLGEN",
                "Not enforced by the site standard.",
            )
        elif not sql_refs:
            record.skip(
                "01", "Every SQL host variable exists in DCLGEN",
                "No qualified SQL host reference found.",
            )
        else:
            record.expect_all(
                "01", "Every SQL host variable exists in DCLGEN",
                sorted({
                    f"{group}.{field}"
                    for group, field in sql_refs
                    if not self._resolves(field, known_hosts)
                }),
            )

        # ---- 02 SQL host belongs to its group -----------------------
        if not sql_refs:
            record.skip(
                "02", "Every SQL host variable belongs to its group",
                "No qualified SQL host reference found.",
            )
        else:
            record.expect_all(
                "02", "Every SQL host variable belongs to its group",
                sorted({
                    f"{group}.{field}"
                    for group, field in sql_refs
                    if self._resolves(field, known_hosts)
                    and not self._resolves(
                        field, group_hosts.get(group, set())
                    )
                }),
            )

        # ---- 03 COBOL qualified names exist in DCLGEN ---------------
        if not cobol_refs:
            record.skip(
                "03", f"Every {std.DCLGEN_GROUP_PREFIX} qualified reference "
                      f"exists in DCLGEN",
                f"No {std.DCLGEN_GROUP_PREFIX} qualified reference found.",
            )
        else:
            record.expect_all(
                "03", f"Every {std.DCLGEN_GROUP_PREFIX} qualified reference "
                      f"exists in DCLGEN",
                sorted({
                    f"{field} OF {group}"
                    for group, field in cobol_refs
                    if not self._resolves(field, known_hosts)
                }),
            )

        # ---- 04 COBOL qualified name belongs to its group -----------
        if not cobol_refs:
            record.skip(
                "04", f"Every {std.DCLGEN_GROUP_PREFIX} qualified reference "
                      f"belongs to its group",
                f"No {std.DCLGEN_GROUP_PREFIX} qualified reference found.",
            )
        else:
            record.expect_all(
                "04", f"Every {std.DCLGEN_GROUP_PREFIX} qualified reference "
                      f"belongs to its group",
                sorted({
                    f"{field} OF {group}"
                    for group, field in cobol_refs
                    if self._resolves(field, known_hosts)
                    and not self._resolves(
                        field, group_hosts.get(group, set())
                    )
                }),
            )

        # ---- 05 every group is a real DCLGEN group ------------------
        groups = {group for group, _ in sql_refs} | {
            group for group, _ in cobol_refs
        }
        tables = meta.dclgen_tables(ctx)
        record.expect_all(
            "05", f"Every {std.DCLGEN_GROUP_PREFIX} group matches a DCLGEN "
                  f"table",
            sorted(
                group for group in groups
                if group.startswith(prefix)
                and group[len(prefix):] not in tables
            ),
        )

    # ---- helpers ----------------------------------------------------
    @staticmethod
    def _resolves(field: str, hosts: set[str]) -> bool:
        """True when a name is a DCLGEN host or a VARCHAR subfield of one.

        DCLGEN declares a VARCHAR column as a group with two 49-level
        children. DclgenParser keeps only fields carrying a PIC or USAGE,
        so neither the group nor its children reach the review. A name
        ending in a known VARCHAR suffix whose stem is a real host is
        therefore valid, not a defect in the generated code.
        """
        if field in hosts:
            return True
        for suffix in std.VARCHAR_SUBFIELD_SUFFIXES:
            if field.endswith(suffix) and field[: -len(suffix)] in hosts:
                return True
        return False

    @staticmethod
    def _all_hosts(ctx) -> set[str]:
        out: set[str] = set()
        for table in meta.dclgen_tables(ctx):
            out.update(meta.hosts_for_table(ctx, table).values())
        return out

    @staticmethod
    def _hosts_by_group(ctx) -> dict[str, set[str]]:
        prefix = std.DCLGEN_GROUP_PREFIX.upper()
        out: dict[str, set[str]] = {}
        for table in meta.dclgen_tables(ctx):
            out[f"{prefix}{table}"] = set(
                meta.hosts_for_table(ctx, table).values()
            )
        return out

    @staticmethod
    def _sql_references(view) -> set[tuple[str, str]]:
        return {
            (match.group("group"), match.group("field"))
            for block in sql.sql_blocks(view)
            for match in HOST_DOT.finditer(block.text)
        }

    @staticmethod
    def _cobol_references(view, prefix: str) -> set[tuple[str, str]]:
        out: set[tuple[str, str]] = set()
        for line in view.code:
            for match in QUALIFIED.finditer(sql.norm(line.logical)):
                if match.group("group").startswith(prefix):
                    out.add((match.group("group"), match.group("field")))
        return out