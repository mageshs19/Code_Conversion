# LOCATION: code_review/checks/chk_02_db2_infrastructure.py
# ACTION: REPLACE ENTIRE FILE

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

DEFAULT_SOURCE_COPYBOOK = "SQLERRWS"


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
        # ---- 01 required tokens --------------------------------------
        record.expect_all(
            "01", "Required DB2 tokens are present",
            [t for t in std.REQUIRED_TOKENS if not view.has_code_token(t)],
        )

        code = statements([l.logical for l in view.code])

        # ---- 02 each required include exactly once -------------------
        wrong = [
            (t, code.count(norm(t)))
            for t in std.REQUIRED_LINES
            if code.count(norm(t)) != 1
        ]
        record.expect_all(
            "02", "Each required include is declared exactly once",
            [f"{t} (found {n})" for t, n in wrong],
        )

        # ---- 03 SQL-LOCATION ownership -------------------------------
        self._review_sql_location(code, record)

        # ---- 04 / 05 section markers ---------------------------------
        ws_at = next((i for i, line in enumerate(code) if WS.match(line)), -1)
        pd_at = next((i for i, line in enumerate(code) if PD.match(line)), -1)

        record.expect("04", "WORKING-STORAGE SECTION is present", ws_at >= 0)
        record.expect("05", "PROCEDURE DIVISION is present", pd_at >= 0)

        # ---- 06 infrastructure placement -----------------------------
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

        # ---- 07 marker uniqueness ------------------------------------
        record.expect_none(
            "07", "No generated block marker is duplicated",
            [
                f"{m} x{view.count_of(m)}"
                for m in std.UNIQUE_MARKERS
                if view.count_of(m) > 1
            ],
        )

        # ---- 08 no TODO or warning marker ----------------------------
        record.expect_none(
            "08", "No TODO or warning marker remains",
            [m for m in std.FORBIDDEN_MARKERS if view.has_token(m)],
        )

    # =================================================================
    # Criterion 03
    # =================================================================
    def _review_sql_location(self, code: list[str], record) -> None:
        """SQL-LOCATION is declared, or deliberately supplied elsewhere.

        Two site standards are possible and both are legitimate:

          ENFORCE_SQL_LOCATION_DECLARATION = True
              the program declares 01 SQL-LOCATION itself.

          ENFORCE_SQL_LOCATION_DECLARATION = False
              SQLERRWS supplies it. A local declaration is then a
              DUPLICATE DATA-NAME and the compiler rejects the program,
              so a declaration found here is a FAILURE, not a pass.

        The flag is therefore tested BEFORE the field is looked for.
        Testing presence first made the second standard unreachable: the
        absent field failed the check before the flag was ever consulted.
        """
        title = f"{std.SQL_LOCATION_FIELD} is declared"

        pics = [
            m.group("pic").strip()
            for m in (SQL_LOC.match(line) for line in code)
            if m
        ]

        enforce = getattr(std, "ENFORCE_SQL_LOCATION_DECLARATION", True)

        if enforce:
            if pics:
                record.ok("03", title)
            else:
                record.fail("03", title, note="Field not found.")
            return

        copybook = getattr(
            std, "SQL_LOCATION_SOURCE_COPYBOOK", DEFAULT_SOURCE_COPYBOOK
        )

        if pics:
            record.fail(
                "03",
                f"{std.SQL_LOCATION_FIELD} is not declared locally",
                note=(
                    f"{copybook} already declares {std.SQL_LOCATION_FIELD}. "
                    f"A second declaration is a duplicate data-name. "
                    f"Found: {', '.join(pics)}"
                ),
            )
            return

        record.skip(
            "03",
            title,
            f"{std.SQL_LOCATION_FIELD} is supplied by {copybook}, "
            f"not declared in the program.",
        )