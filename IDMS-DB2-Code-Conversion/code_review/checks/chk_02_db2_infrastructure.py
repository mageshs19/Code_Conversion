"""CHK-02 DB2 infrastructure declarations."""

from __future__ import annotations

import re

from code_review.engine.check_base import CRITICAL, Check
from code_review.standards import cobol_standards as std

WS = re.compile(r"^WORKING-STORAGE\s+SECTION\s*\.?$")
PD = re.compile(r"^PROCEDURE\s+DIVISION\b")
SQL_LOC = re.compile(r"^(?:01|05|77)\s+SQL-LOCATION\s+(?P<pic>PIC\s+.*)$")

WS_RUN = re.compile(r"\s+")
EXEC_SQL_START = "EXEC SQL"
EXEC_SQL_END = "END-EXEC"


def norm(text: str) -> str:
    """Uppercase, trimmed, with every internal whitespace run collapsed."""
    return WS_RUN.sub(" ", str(text or "").strip().upper())


def statements(lines: list[str]) -> list[str]:
    """Logical statements, with EXEC SQL ... END-EXEC. joined into one entry.

    Ordering is preserved, so positional criteria stay valid. A non-SQL line
    maps one-to-one onto a single statement.
    """
    out: list[str] = []
    buffer: list[str] = []
    inside = False

    for raw in lines:
        line = norm(raw)

        if not inside and line.startswith(EXEC_SQL_START):
            inside = True
            buffer = [line]
            if EXEC_SQL_END in line:
                out.append(" ".join(buffer))
                inside, buffer = False, []
            continue

        if inside:
            buffer.append(line)
            if EXEC_SQL_END in line:
                out.append(" ".join(buffer))
                inside, buffer = False, []
            continue

        out.append(line)

    if buffer:
        out.append(" ".join(buffer))
    return out


class Db2InfrastructureCheck(Check):
    CHECK_ID = "CHK-02"
    TITLE = "DB2 infrastructure declarations"
    SEVERITY = CRITICAL
    ORDER = 20

    def review(self, ctx, view, record):
        record.expect_all(
            "01", "Required DB2 tokens are present",
            [t for t in std.REQUIRED_TOKENS if not view.has_code_token(t)],
        )

        code = statements([l.logical for l in view.code])

        wrong = [
            (t, code.count(norm(t)))
            for t in std.REQUIRED_LINES
            if code.count(norm(t)) != 1
        ]
        record.expect_all(
            "02", "Each required include is declared exactly once",
            [f"{t} (found {n})" for t, n in wrong],
        )

        pics = [
            m.group("pic").strip()
            for m in (SQL_LOC.match(line) for line in code)
            if m
        ]
        if not pics:
            record.fail(
                "03", f"{std.SQL_LOCATION_FIELD} is declared",
                note="Field not found.",
            )
        else:
            record.expect(
                "03", f"{std.SQL_LOCATION_FIELD} uses {std.SQL_LOCATION_PICTURE}",
                all(p == norm(std.SQL_LOCATION_PICTURE) for p in pics),
                note=f"found {pics}",
            )

        ws_at = next((i for i, line in enumerate(code) if WS.match(line)), -1)
        pd_at = next((i for i, line in enumerate(code) if PD.match(line)), -1)

        record.expect("04", "WORKING-STORAGE SECTION is present", ws_at >= 0)
        record.expect("05", "PROCEDURE DIVISION is present", pd_at >= 0)

        if ws_at >= 0 and pd_at >= 0:
            late = []
            for required in std.REQUIRED_LINES:
                key = norm(required)
                at = code.index(key) if key in code else -1
                if at >= 0 and not (ws_at < at < pd_at):
                    late.append(required)
            record.expect_all(
                "06", "Infrastructure sits inside WORKING-STORAGE", late,
            )
        else:
            record.skip(
                "06", "Infrastructure placement", "Section markers not found.",
            )

        record.expect_none(
            "07", "No generated block marker is duplicated",
            [
                f"{m} x{view.count_of(m)}"
                for m in std.UNIQUE_MARKERS
                if view.count_of(m) > 1
            ],
        )
        record.expect_none(
            "08", "No TODO or warning marker remains",
            [m for m in std.FORBIDDEN_MARKERS if view.has_token(m)],
        )