"""CHK-19 Restart paragraph structure."""

from __future__ import annotations

import re

from code_review.engine import cursors, sql_blocks as sql
from code_review.engine.check_base import MAJOR, UPDATE, Check
from code_review.standards import cobol_standards as std

PARAGRAPH = re.compile(r"^(?P<name>[A-Z0-9][A-Z0-9-]*)\.$")
RESTART_SQL_PARAGRAPH = re.compile(
    r"^(?P<number>\d{3})-(?P<operation>SELECT|UPDATE|INSERT)-"
    r"(?P<table>[A-Z0-9]+)\.$"
)


class RestartParagraphStructureCheck(Check):
    CHECK_ID = "CHK-19"
    TITLE = "Restart paragraph structure"
    SEVERITY = MAJOR
    APPLIES_TO = UPDATE
    ORDER = 190

    def relevant(self, ctx, view) -> bool:
        return bool(self._declared(view))

    def not_relevant_reason(self) -> str:
        return (
            "No generated restart paragraph found. The legacy IDMS restart "
            "flow is preserved, pending Sheet Mapping input (decision D-3)."
        )

    def review(self, ctx, view, record):
        declared = self._declared(view)
        performed = cursors.performed_names(view)
        expected = set(std.RESTART_PARAGRAPHS.values())

        # ---- 01 the standard set is complete ------------------------
        record.expect_all(
            "01", "Every standard restart paragraph is declared",
            sorted(expected - declared.keys()),
        )

        # ---- 02 each declared once ----------------------------------
        repeated = sorted(
            name for name, lines in declared.items()
            if name in expected and len(lines) > 1
        )
        record.expect_all(
            "02", "Each restart paragraph is declared exactly once", repeated,
        )

        # ---- 03 each is reachable -----------------------------------
        record.expect_all(
            "03", "Every restart paragraph is reachable",
            sorted(
                name for name in declared
                if name in expected
                and name != std.RESTART_PARAGRAPHS["control"]
                and name not in performed
            ),
        )

        # ---- 04 restart SQL paragraphs exist ------------------------
        sql_paragraphs = self._restart_sql_paragraphs(view)
        if not sql_paragraphs:
            record.skip(
                "04", "Restart SELECT, UPDATE and INSERT paragraphs exist",
                "No restart SQL paragraph generated.",
            )
        else:
            found = {p["operation"] for p in sql_paragraphs}
            record.expect_all(
                "04", "Restart SELECT, UPDATE and INSERT paragraphs exist",
                sorted(set(std.RESTART_SQL_OPERATIONS) - found),
            )

        # ---- 05 restart SQL paragraphs are numbered consistently ----
        if not sql_paragraphs:
            record.skip(
                "05", f"Restart SQL paragraphs use the "
                      f"{std.RESTART_SQL_PARAGRAPH_PREFIX} prefix",
                "No restart SQL paragraph generated.",
            )
        else:
            record.expect_all(
                "05", f"Restart SQL paragraphs use the "
                      f"{std.RESTART_SQL_PARAGRAPH_PREFIX} prefix",
                [
                    p["name"] for p in sql_paragraphs
                    if not p["name"].startswith(
                        std.RESTART_SQL_PARAGRAPH_PREFIX
                    )
                ],
            )

        # ---- 06 the abend paragraph calls the abend routine ---------
        abend = std.RESTART_PARAGRAPHS["abend"]
        if abend not in declared:
            record.skip(
                "06", f"{abend} calls {std.RESTART_ABEND_CALL}",
                "Abend paragraph not declared.",
            )
        else:
            body = self._paragraph_body(view, declared[abend][0])
            record.expect(
                "06", f"{abend} calls {std.RESTART_ABEND_CALL}",
                any(std.RESTART_ABEND_CALL in line for line in body),
                note="Abend call not found in the paragraph body.",
            )

        # ---- 07 the control paragraph drives the select -------------
        control = std.RESTART_PARAGRAPHS["control"]
        if control not in declared:
            record.skip(
                "07", f"{control} performs a restart SELECT",
                "Control paragraph not declared.",
            )
        else:
            body = self._paragraph_body(view, declared[control][0])
            record.expect(
                "07", f"{control} performs a restart SELECT",
                any(
                    line.startswith("PERFORM")
                    and "SELECT" in line
                    for line in body
                ),
                note="No PERFORM of a restart SELECT paragraph found.",
            )

    # ---- helpers ----------------------------------------------------
    @staticmethod
    def _declared(view) -> dict[str, list]:
        out: dict[str, list] = {}
        for line in view.code:
            match = PARAGRAPH.match(sql.norm(line.logical))
            if not match:
                continue
            name = match.group("name")
            if name in std.NON_PARAGRAPH_WORDS:
                continue
            if name in std.RESTART_PARAGRAPHS.values() or (
                name.startswith(std.RESTART_SQL_PARAGRAPH_PREFIX)
            ):
                out.setdefault(name, []).append(line)
        return out

    @staticmethod
    def _restart_sql_paragraphs(view) -> list[dict]:
        out = []
        for line in view.code:
            match = RESTART_SQL_PARAGRAPH.match(sql.norm(line.logical))
            if match:
                out.append({
                    "name": sql.norm(line.logical).rstrip("."),
                    "operation": match.group("operation"),
                    "table": match.group("table"),
                    "line": line,
                })
        return out

    @staticmethod
    def _paragraph_body(view, header) -> list[str]:
        code = view.code
        start = next(
            (i for i, line in enumerate(code) if line.number == header.number),
            -1,
        )
        if start < 0:
            return []
        out = []
        for line in code[start + 1:]:
            logical = sql.norm(line.logical)
            if PARAGRAPH.match(logical) and (
                logical[:-1] not in std.NON_PARAGRAPH_WORDS
            ):
                break
            out.append(logical)
        return out