"""CHK-07 Sequence numbering continuity."""

from __future__ import annotations

from collections import Counter

from code_review.engine.check_base import MAJOR, Check
from code_review.standards import cobol_standards as std


class SequenceContinuityCheck(Check):
    CHECK_ID = "CHK-07"
    TITLE = "Sequence numbering continuity"
    SEVERITY = MAJOR
    ORDER = 70

    def relevant(self, ctx, view) -> bool:
        return any(line.is_fixed for line in view.lines)

    def not_relevant_reason(self) -> str:
        return "Program has no fixed-format sequenced lines."

    def review(self, ctx, view, record):
        left = view.sequence()
        right = view.sequence(right=True)
        fixed = [line for line in view.lines if line.is_fixed]

        # ---- 01 every populated line carries both sequences ----------
        record.expect_none(
            "01", "Every populated line carries both sequence numbers",
            [line for line in view.populated if not line.is_fixed],
        )

        # ---- 02 / 03 left sequence ascends and steps ----------------
        self._ascending(record, "02", "Left sequence ascends", left)
        self._step(
            record, "03", "Left sequence",
            left, std.LEFT_SEQUENCE_STEP,
        )

        # ---- 04 / 05 right sequence ascends and steps ---------------
        self._ascending(record, "04", "Right sequence ascends", right)
        self._step(
            record, "05", "Right sequence",
            right, std.RIGHT_SEQUENCE_STEP,
        )

        # ---- 06 / 07 start values -----------------------------------
        if not std.ENFORCE_SEQUENCE_START:
            record.skip(
                "06", "Left sequence start value",
                "Not enforced by the site standard.",
            )
            record.skip(
                "07", "Right sequence start value",
                "Not enforced by the site standard.",
            )
        else:
            record.expect(
                "06", f"Left sequence starts at {std.LEFT_SEQUENCE_START}",
                bool(left) and left[0] == std.LEFT_SEQUENCE_START,
                note=f"found {left[0] if left else 'none'}",
            )
            record.expect(
                "07", f"Right sequence starts at {std.RIGHT_SEQUENCE_START}",
                bool(right) and right[0] == std.RIGHT_SEQUENCE_START,
                note=f"found {right[0] if right else 'none'}",
            )

        # ---- 08 / 09 duplicates -------------------------------------
        self._unique(record, "08", "Left sequence", left)
        self._unique(record, "09", "Right sequence", right)

        # ---- 10 counts agree ----------------------------------------
        record.expect(
            "10", "Left and right sequences cover the same lines",
            len(left) == len(right) == len(fixed),
            note=f"left {len(left)}, right {len(right)}, fixed {len(fixed)}",
        )

    # ---- helpers ----------------------------------------------------
    @staticmethod
    def _ascending(record, num: str, description: str, values: list[int]) -> None:
        if len(values) < 2:
            record.skip(num, description, "Fewer than two sequenced lines.")
            return
        breaks = [
            f"{a} then {b}"
            for a, b in zip(values, values[1:])
            if b <= a
        ]
        record.expect_all(
            num, description, breaks,
            note=(
                "not ascending at: " + ", ".join(breaks[:10])
                if breaks else ""
            ),
        )

    @staticmethod
    def _step(
        record,
        num: str,
        label: str,
        values: list[int],
        expected: int,
    ) -> None:
        description = f"{label} step is {expected}"

        if not std.ENFORCE_SEQUENCE_STEP:
            record.skip(num, description, "Step not enforced by the standard.")
            return
        if len(values) < 2:
            record.skip(num, description, "Fewer than two sequenced lines.")
            return

        wrong = [
            f"{a} -> {b} (step {b - a})"
            for a, b in zip(values, values[1:])
            if (b - a) != expected
        ]
        if wrong and std.ALLOW_SEQUENCE_GAPS:
            wrong = [
                item for item in wrong
                if item.endswith("(step 0)") or "-" in item.split("step ")[-1]
            ]
        record.expect_all(
            num, description, wrong,
            note=(
                f"{len(wrong)} irregular step(s): " + ", ".join(wrong[:10])
                if wrong else ""
            ),
        )

    @staticmethod
    def _unique(record, num: str, label: str, values: list[int]) -> None:
        description = f"{label} numbers are unique"
        if not values:
            record.skip(num, description, "No sequenced lines.")
            return
        duplicates = [
            f"{value} x{count}"
            for value, count in sorted(Counter(values).items())
            if count > 1
        ]
        record.expect_all(
            num, description, duplicates,
            note=(
                f"{len(duplicates)} duplicated value(s)"
                if duplicates else ""
            ),
        )