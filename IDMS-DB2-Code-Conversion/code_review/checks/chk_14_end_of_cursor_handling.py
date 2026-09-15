"""CHK-14 End-of-cursor handling in the fetch paragraph."""

from __future__ import annotations

from code_review.engine import cursors, sql_blocks as sql
from code_review.engine.check_base import MAJOR, RETRIEVAL, Check
from code_review.standards import cobol_standards as std


class EndOfCursorHandlingCheck(Check):
    CHECK_ID = "CHK-14"
    TITLE = "End-of-cursor handling"
    SEVERITY = MAJOR
    APPLIES_TO = RETRIEVAL
    ORDER = 140

    def relevant(self, ctx, view) -> bool:
        return bool(cursors.cursor_paragraphs(view))

    def not_relevant_reason(self) -> str:
        return "Program contains no generated cursor paragraph."

    def review(self, ctx, view, record):
        sets = cursors.paragraph_sets(view)
        fetches = [
            group["FETCH"] for group in sets.values() if "FETCH" in group
        ]
        opens = [
            group["OPEN"] for group in sets.values() if "OPEN" in group
        ]

        # ---- 01 FETCH handles WHEN 100 ------------------------------
        if not fetches:
            record.skip(
                "01", f"Every FETCH paragraph handles "
                      f"{std.SQLCODE_NOT_FOUND_BRANCH}",
                "Program contains no FETCH paragraph.",
            )
        else:
            record.expect_none(
                "01", f"Every FETCH paragraph handles "
                      f"{std.SQLCODE_NOT_FOUND_BRANCH}",
                [
                    para for para in fetches
                    if not self._body_has(
                        view, para, std.SQLCODE_NOT_FOUND_BRANCH,
                    )
                ],
            )

        # ---- 02 WHEN 100 sets the EOC flag --------------------------
        if not fetches:
            record.skip(
                "02", "Every FETCH paragraph sets the end-of-cursor flag",
                "Program contains no FETCH paragraph.",
            )
        else:
            record.expect_none(
                "02", "Every FETCH paragraph sets the end-of-cursor flag",
                [
                    para for para in fetches
                    if not self._body_has(
                        view,
                        para,
                        f"SET {para.cursor}{std.CURSOR_EOC_SUFFIX} TO TRUE",
                    )
                ],
            )

        # ---- 03 OPEN resets the flag --------------------------------
        if not opens:
            record.skip(
                "03", "Every OPEN paragraph resets the end-of-cursor flag",
                "Program contains no OPEN paragraph.",
            )
        else:
            record.expect_none(
                "03", "Every OPEN paragraph resets the end-of-cursor flag",
                [
                    para for para in opens
                    if not self._body_has(
                        view,
                        para,
                        f"SET {para.cursor}{std.CURSOR_NOT_EOC_SUFFIX} "
                        f"TO TRUE",
                    )
                ],
            )

        # ---- 04 loops test the flag, not SQLCODE --------------------
        if not std.ENFORCE_EOC_FLAG_LOOP:
            record.skip(
                "04", "Fetch loops test the end-of-cursor flag",
                "Not enforced by the site standard.",
            )
        else:
            record.expect_none(
                "04", "Fetch loops test the end-of-cursor flag",
                [
                    line for line in view.code
                    if any(
                        legacy in sql.norm(line.logical)
                        for legacy in std.LEGACY_EOC_CONDITIONS
                    )
                ],
            )

        # ---- 05 each fetch is performed UNTIL its flag --------------
        if not fetches:
            record.skip(
                "05", "Every FETCH paragraph is performed until its flag",
                "Program contains no FETCH paragraph.",
            )
        else:
            code = [sql.norm(line.logical) for line in view.code]
            missing = []
            for para in fetches:
                wanted = (
                    f"PERFORM {para.name} UNTIL "
                    f"{para.cursor}{std.CURSOR_EOC_SUFFIX}"
                )
                if not any(line.startswith(wanted) for line in code):
                    missing.append(wanted)
            record.expect_all(
                "05", "Every FETCH paragraph is performed until its flag",
                missing,
            )

        # ---- 06 flag block marker present ---------------------------
        record.expect(
            "06", f"Generated block marker '{std.CURSOR_FLAGS_MARKER}' "
                  f"is present",
            view.has_token(std.CURSOR_FLAGS_MARKER),
            note="Marker comment not found.",
        )

    # ---- helpers ----------------------------------------------------
    @staticmethod
    def _body_has(view, para, token: str) -> bool:
        wanted = sql.norm(token)
        body = cursors.paragraph_body(
            view, para, stop_words=std.NON_PARAGRAPH_WORDS,
        )
        return any(wanted in line for line in body)