"""CHK-12 Cursor declaration standard."""

from __future__ import annotations

from code_review.engine import cursors
from code_review.engine.check_base import CRITICAL, RETRIEVAL, Check
from code_review.standards import cobol_standards as std


class CursorDeclarationCheck(Check):
    CHECK_ID = "CHK-12"
    TITLE = "Cursor declaration standard"
    SEVERITY = CRITICAL
    APPLIES_TO = RETRIEVAL
    ORDER = 120

    def relevant(self, ctx, view) -> bool:
        return bool(cursors.declare_blocks(view))

    def not_relevant_reason(self) -> str:
        return "Program declares no DB2 cursor."

    def review(self, ctx, view, record):
        blocks = cursors.declare_blocks(view)
        declared = cursors.declared_cursors(view)

        # ---- 01 WITH HOLD -------------------------------------------
        if not std.ENFORCE_CURSOR_WITH_HOLD:
            record.skip(
                "01", "Every cursor is declared WITH HOLD",
                "Not enforced by the site standard.",
            )
        else:
            record.expect_none(
                "01", "Every cursor is declared WITH HOLD",
                [b for b in blocks if not b.has("WITH HOLD")],
            )

        # ---- 02 FOR READ ONLY ---------------------------------------
        if not std.ENFORCE_CURSOR_FOR_READ_ONLY:
            record.skip(
                "02", "Every cursor is declared FOR READ ONLY",
                "Not enforced by the site standard.",
            )
        else:
            record.expect_none(
                "02", "Every cursor is declared FOR READ ONLY",
                [b for b in blocks if not b.has("FOR READ ONLY")],
            )

        # ---- 03 SELECT and FROM -------------------------------------
        record.expect_none(
            "03", "Every cursor declaration has SELECT and FROM",
            [
                b for b in blocks
                if not all(b.has(c) for c in std.CURSOR_SELECT_CLAUSES)
            ],
        )

        # ---- 04 explicit columns ------------------------------------
        if not std.ENFORCE_CURSOR_EXPLICIT_COLUMNS:
            record.skip(
                "04", "No cursor selects every column",
                "Not enforced by the site standard.",
            )
        else:
            record.expect_none(
                "04", "No cursor selects every column",
                [b for b in blocks if std.CURSOR_SELECT_ALL in b.text],
            )

        # ---- 05 each cursor declared once ---------------------------
        names = [
            cursors.DECLARE.search(b.text).group("cursor").upper()
            for b in blocks
            if cursors.DECLARE.search(b.text)
        ]
        repeated = sorted({n for n in names if names.count(n) > 1})
        record.expect_all(
            "05", "Each cursor is declared exactly once", repeated,
        )

        # ---- 06 declarations precede PROCEDURE DIVISION -------------
        pd_line = self._procedure_division_line(view)
        if pd_line <= 0:
            record.skip(
                "06", "Cursor declarations precede PROCEDURE DIVISION",
                "PROCEDURE DIVISION not found.",
            )
        else:
            record.expect_none(
                "06", "Cursor declarations precede PROCEDURE DIVISION",
                [b for b in blocks if b.line_number > pd_line],
            )

        # ---- 07 every opened cursor is declared ---------------------
        opened = cursors.cursors_used(view, "OPEN")
        if not opened:
            record.skip(
                "07", "Every opened cursor is declared",
                "No EXEC SQL OPEN found.",
            )
        else:
            record.expect_all(
                "07", "Every opened cursor is declared",
                sorted(name for name in opened if name not in declared),
            )

        # ---- 08 declaration block marker present --------------------
        record.expect(
            "08", f"Generated block marker '{std.CURSOR_DECLARATION_MARKER}' "
                  f"is present",
            view.has_token(std.CURSOR_DECLARATION_MARKER),
            note="Marker comment not found.",
        )

    # ---- helpers ----------------------------------------------------
    @staticmethod
    def _procedure_division_line(view) -> int:
        for line in view.code:
            if line.logical.startswith("PROCEDURE DIVISION"):
                return line.number
        return -1