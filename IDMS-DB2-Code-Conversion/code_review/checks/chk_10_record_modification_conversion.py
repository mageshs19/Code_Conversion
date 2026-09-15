"""CHK-10 Record modification conversion."""

from __future__ import annotations

from code_review.engine import sql_blocks as sql
from code_review.engine.check_base import CRITICAL, UPDATE, Check
from code_review.standards import cobol_standards as std


class RecordModificationConversionCheck(Check):
    CHECK_ID = "CHK-10"
    TITLE = "Record modification conversion"
    SEVERITY = CRITICAL
    APPLIES_TO = UPDATE
    ORDER = 100

    def relevant(self, ctx, view) -> bool:
        return view.has_code_token(std.SQL_BLOCK_START)

    def not_relevant_reason(self) -> str:
        return "Program contains no embedded SQL."

    def review(self, ctx, view, record):
        # Restart writes carry their own QUERYNOs and are scored by CHK-20.
        blocks = [
            b for b in sql.sql_blocks(view)
            if not sql.targets_restart(b, std.RESTART_TABLE_NAME_HINTS)
        ]
        writes = [b for b in blocks if b.verb in std.WRITE_SQL_VERBS]
        inserts = [b for b in writes if b.verb == "INSERT"]
        updates = [b for b in writes if b.verb == "UPDATE"]
        deletes = [b for b in writes if b.verb == "DELETE"]

        # ---- 01 no business write was skipped -----------------------
        record.expect_none(
            "01", "No business write was skipped for missing metadata",
            [
                line for line in view.comments
                if any(m in line.logical for m in std.MISSING_MAPPING_MARKERS)
                and not any(
                    hint in line.logical
                    for hint in std.RESTART_CONTROL_HINTS
                )
            ],
        )

        # ---- 02 the program actually writes -------------------------
        if not writes:
            record.skip(
                "02", "Update program issues at least one business write",
                "No business INSERT, UPDATE or DELETE found. Only restart "
                "writes were generated.",
            )
        else:
            record.ok(
                "02", "Update program issues at least one business write",
            )

        # ---- 03 INSERT names a target -------------------------------
        if not inserts:
            record.skip(
                "03", "Every INSERT names a target table",
                "Program contains no business INSERT.",
            )
        else:
            record.expect_none(
                "03", "Every INSERT names a target table",
                [
                    b for b in inserts
                    if not all(b.has(c) for c in std.INSERT_REQUIRED_CLAUSES)
                ],
            )

        # ---- 04 UPDATE has SET and WHERE ----------------------------
        if not updates:
            record.skip(
                "04", "Every UPDATE has SET and WHERE",
                "Program contains no business UPDATE.",
            )
        else:
            record.expect_none(
                "04", "Every UPDATE has SET and WHERE",
                [
                    b for b in updates
                    if not all(b.has(c) for c in std.UPDATE_REQUIRED_CLAUSES)
                ],
            )

        # ---- 05 DELETE is key qualified -----------------------------
        if not deletes:
            record.skip(
                "05", "Every DELETE is key qualified",
                "Program contains no business DELETE.",
            )
        else:
            record.expect_none(
                "05", "Every DELETE is key qualified",
                [
                    b for b in deletes
                    if not all(b.has(c) for c in std.DELETE_REQUIRED_CLAUSES)
                ],
            )

        # ---- 06 QUERYNO present -------------------------------------
        if not std.ENFORCE_QUERYNO:
            record.skip(
                "06", f"Every business write carries QUERYNO "
                      f"{std.UPDATE_QUERYNO}",
                "QUERYNO not enforced by the site standard.",
            )
        elif not writes:
            record.skip(
                "06", f"Every business write carries QUERYNO "
                      f"{std.UPDATE_QUERYNO}",
                "Program contains no business write statement.",
            )
        else:
            expected = f"QUERYNO {std.UPDATE_QUERYNO}"
            record.expect_none(
                "06", f"Every business write carries QUERYNO "
                      f"{std.UPDATE_QUERYNO}",
                [b for b in writes if expected not in b.text],
            )

        # ---- 07 SQL-LOCATION set before each write ------------------
        if not std.ENFORCE_SQL_LOCATION_BEFORE_SQL:
            record.skip(
                "07", f"{std.SQL_LOCATION_FIELD} is set before each "
                      f"business write",
                "Not enforced by the site standard.",
            )
        elif not writes:
            record.skip(
                "07", f"{std.SQL_LOCATION_FIELD} is set before each "
                      f"business write",
                "Program contains no business write statement.",
            )
        else:
            record.expect_none(
                "07", f"{std.SQL_LOCATION_FIELD} is set before each "
                      f"business write",
                [
                    b for b in writes
                    if not self._location_set_before(view, b)
                ],
            )

    # ---- helpers ----------------------------------------------------
    @staticmethod
    def _location_set_before(view, block) -> bool:
        window = sql.lines_before(view, block, std.SQL_LOCATION_LOOKBACK)
        return any(
            line.startswith(std.SQL_LOCATION_MOVE_PREFIX)
            and std.SQL_LOCATION_MOVE_SUFFIX in line
            for line in window
        )