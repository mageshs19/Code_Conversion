"""CHK-09 Record retrieval conversion."""

from __future__ import annotations

from code_review.engine import sql_blocks as sql
from code_review.engine.check_base import MAJOR, Check
from code_review.standards import cobol_standards as std


class RecordRetrievalConversionCheck(Check):
    CHECK_ID = "CHK-09"
    TITLE = "Record retrieval conversion"
    SEVERITY = MAJOR
    ORDER = 90

    def relevant(self, ctx, view) -> bool:
        return view.has_code_token(std.SQL_BLOCK_START)

    def not_relevant_reason(self) -> str:
        return "Program contains no embedded SQL."

    def review(self, ctx, view, record):
        # Restart SQL is scored by CHK-19, CHK-20 and CHK-21.
        blocks = [
            b for b in sql.sql_blocks(view)
            if not sql.targets_restart(b, std.RESTART_TABLE_NAME_HINTS)
        ]
        selects = [b for b in blocks if b.verb == "SELECT"]
        retrieval = [b for b in blocks if b.verb in std.RETRIEVAL_SQL_VERBS]

        # ---- 01 nothing was skipped for missing metadata ------------
        record.expect_none(
            "01", "No business retrieval was skipped for missing metadata",
            [
                line for line in view.comments
                if any(m in line.logical for m in std.MISSING_MAPPING_MARKERS)
                and not any(
                    hint in line.logical
                    for hint in std.RESTART_CONTROL_HINTS
                )
            ],
        )

        # ---- 02 SELECT has FROM -------------------------------------
        if not selects:
            record.skip(
                "02", "Every SELECT names a source table",
                "Program contains no business singleton SELECT.",
            )
        else:
            record.expect_none(
                "02", "Every SELECT names a source table",
                [b for b in selects if not b.has("FROM")],
            )

        # ---- 03 SELECT has INTO -------------------------------------
        if not selects:
            record.skip(
                "03", "Every SELECT retrieves into host variables",
                "Program contains no business singleton SELECT.",
            )
        else:
            record.expect_none(
                "03", "Every SELECT retrieves into host variables",
                [b for b in selects if not b.has("INTO")],
            )

        # ---- 04 SELECT has WHERE ------------------------------------
        if not std.ENFORCE_SELECT_WHERE:
            record.skip(
                "04", "Every SELECT is key qualified",
                "Not enforced by the site standard.",
            )
        elif not selects:
            record.skip(
                "04", "Every SELECT is key qualified",
                "Program contains no business singleton SELECT.",
            )
        else:
            record.expect_none(
                "04", "Every SELECT is key qualified",
                [b for b in selects if not b.has("WHERE")],
            )

        # ---- 05 SQL-LOCATION set before retrieval -------------------
        if not std.ENFORCE_SQL_LOCATION_BEFORE_SQL:
            record.skip(
                "05",
                f"{std.SQL_LOCATION_FIELD} is set before each retrieval",
                "Not enforced by the site standard.",
            )
        elif not retrieval:
            record.skip(
                "05",
                f"{std.SQL_LOCATION_FIELD} is set before each retrieval",
                "Program contains no business retrieval SQL.",
            )
        else:
            record.expect_none(
                "05",
                f"{std.SQL_LOCATION_FIELD} is set before each retrieval",
                [
                    b for b in retrieval
                    if not self._location_set_before(view, b)
                ],
            )

        # ---- 06 no empty converted block ----------------------------
        empty = self._empty_paragraphs(view)
        if not empty:
            record.ok("06", "No paragraph was left empty by the conversion")
        else:
            record.expect_none(
                "06", "No paragraph was left empty by the conversion", empty,
            )

    # ---- helpers ----------------------------------------------------
    @staticmethod
    def _location_set_before(view, block) -> bool:
        """True when SQL-LOCATION is set within the look-back window.

        Both move forms are accepted:

            MOVE '710-OPEN-DZBEFFC1' TO SQL-LOCATION
            MOVE 710                 TO SQL-LOCATION

        The manual reference uses the bare paragraph number. Matching
        only the quoted form failed every generated cursor paragraph
        while the field was in fact being set correctly.
        """
        prefixes = getattr(
            std,
            "SQL_LOCATION_MOVE_PREFIXES",
            (std.SQL_LOCATION_MOVE_PREFIX,),
        )
        window = sql.lines_before(view, block, std.SQL_LOCATION_LOOKBACK)

        return any(
            line.startswith(tuple(prefixes))
            and std.SQL_LOCATION_MOVE_SUFFIX in line
            for line in window
        )
    @staticmethod
    def _empty_paragraphs(view) -> list:
        """Paragraph headers immediately followed by another header."""
        code = view.code
        out: list = []
        for index, line in enumerate(code[:-1]):
            logical = line.logical
            if not logical.endswith(".") or " " in logical:
                continue
            name = logical[:-1]
            if not name or name in std.NON_PARAGRAPH_WORDS:
                continue
            nxt = code[index + 1].logical
            if nxt.endswith(".") and " " not in nxt:
                following = nxt[:-1]
                if following and following not in std.NON_PARAGRAPH_WORDS:
                    out.append(line)
        return out