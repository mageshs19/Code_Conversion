"""CHK-13 Cursor paragraph structure."""

from __future__ import annotations

from code_review.engine import cursors
from code_review.engine.check_base import MAJOR, RETRIEVAL, Check
from code_review.standards import cobol_standards as std


class CursorParagraphStructureCheck(Check):
    CHECK_ID = "CHK-13"
    TITLE = "Cursor paragraph structure"
    SEVERITY = MAJOR
    APPLIES_TO = RETRIEVAL
    ORDER = 130

    def relevant(self, ctx, view) -> bool:
        return bool(cursors.cursor_paragraphs(view))

    def not_relevant_reason(self) -> str:
        return "Program contains no generated cursor paragraph."

    def review(self, ctx, view, record):
        sets = cursors.paragraph_sets(view)
        paragraphs = cursors.cursor_paragraphs(view)
        declared = cursors.declared_cursors(view)
        performed = cursors.performed_names(view)

        # ---- 01 every declared cursor has a full set ----------------
        if not declared:
            record.skip(
                "01", f"Every cursor has "
                      f"{', '.join(std.CURSOR_OPERATIONS)} paragraphs",
                "Program declares no DB2 cursor.",
            )
        else:
            missing = []
            for name in sorted(declared):
                have = sets.get(name, {})
                for operation in std.CURSOR_OPERATIONS:
                    if operation not in have:
                        missing.append(f"{name} {operation}")
            record.expect_all(
                "01", f"Every cursor has "
                      f"{', '.join(std.CURSOR_OPERATIONS)} paragraphs",
                missing,
            )

        # ---- 02 numbering offsets -----------------------------------
        wrong = []
        for name, group in sorted(sets.items()):
            open_para = group.get("OPEN")
            if open_para is None:
                continue
            base = open_para.number
            expected = {
                "FETCH": base + std.CURSOR_FETCH_OFFSET,
                "CLOSE": base + std.CURSOR_CLOSE_OFFSET,
            }
            for operation, number in expected.items():
                para = group.get(operation)
                if para is not None and para.number != number:
                    wrong.append(
                        f"{name} {operation} is {para.number}, "
                        f"expected {number}"
                    )
        record.expect_all(
            "02", f"FETCH is OPEN plus {std.CURSOR_FETCH_OFFSET}, "
                  f"CLOSE is OPEN plus {std.CURSOR_CLOSE_OFFSET}",
            wrong,
        )

        # ---- 03 open numbers come from the agreed set ---------------
        if not std.ENFORCE_CURSOR_OPEN_NUMBERS:
            record.skip(
                "03", "Cursor OPEN numbers come from the site set",
                "Not enforced by the site standard.",
            )
        else:
            allowed = set(std.CURSOR_OPEN_NUMBERS)
            record.expect_all(
                "03", f"Cursor OPEN numbers come from "
                      f"{std.CURSOR_OPEN_NUMBERS}",
                [
                    f"{group['OPEN'].cursor} opens at {group['OPEN'].number}"
                    for group in sets.values()
                    if "OPEN" in group and group["OPEN"].number not in allowed
                ],
            )

        # ---- 04 each paragraph declared once ------------------------
        names = [p.name for p in paragraphs]
        record.expect_all(
            "04", "Each cursor paragraph is declared exactly once",
            sorted({n for n in names if names.count(n) > 1}),
        )

        # ---- 05 every cursor paragraph sets SQL-LOCATION ------------
        if not std.ENFORCE_SQL_LOCATION_BEFORE_SQL:
            record.skip(
                "05", f"Every cursor paragraph sets "
                      f"{std.SQL_LOCATION_FIELD}",
                "Not enforced by the site standard.",
            )
        else:
            record.expect_none(
                "05", f"Every cursor paragraph sets "
                      f"{std.SQL_LOCATION_FIELD}",
                [
                    para for para in paragraphs
                    if not any(
                        std.SQL_LOCATION_MOVE_SUFFIX in body
                        for body in cursors.paragraph_body(view, para)
                    )
                ],
            )

        # ---- 06 every cursor paragraph is reachable -----------------
        record.expect_all(
            "06", "Every cursor paragraph is reachable",
            [
                para.name for para in paragraphs
                if para.name not in performed
            ],
        )

        # ---- 07 generated block marker present ----------------------
        record.expect(
            "07", f"Generated block marker '{std.CURSOR_PARAGRAPH_MARKER}' "
                  f"is present",
            view.has_token(std.CURSOR_PARAGRAPH_MARKER),
            note="Marker comment not found.",
        )