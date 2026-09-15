"""CHK-01 Fixed format 80-column layout."""

from __future__ import annotations

from code_review.engine.check_base import CRITICAL, Check
from code_review.standards import cobol_standards as std


class LineLayoutCheck(Check):
    CHECK_ID = "CHK-01"
    TITLE = "Fixed format 80-column layout"
    SEVERITY = CRITICAL
    ORDER = 10

    def review(self, ctx, view, record):
        lines = view.populated

        record.expect_none(
            "01", f"Every line is exactly {std.LINE_WIDTH} characters",
            [l for l in lines if len(l.raw) != std.LINE_WIDTH],
        )
        record.expect_none(
            "02", "Columns 1-6 hold a numeric sequence number",
            [l for l in lines if not l.raw[0:6].isdigit()],
        )
        record.expect_none(
            "03", "Column 7 holds a valid indicator",
            [l for l in lines if l.indicator not in std.VALID_INDICATORS],
        )
        record.expect_none(
            "04", f"Body stays within columns {std.BODY_FIRST_COLUMN}-{std.BODY_LAST_COLUMN}",
            [l for l in lines if l.overflow.strip()],
        )
        record.expect_none(
            "05", "Columns 73-80 hold a numeric sequence number",
            [l for l in lines if not l.raw[72:80].isdigit()],
        )
        record.expect_none(
            "06", "No sequence digits left inside the body",
            [l for l in lines if l.has_sequence_in_body],
        )

        left, right = view.sequence(), view.sequence(right=True)
        record.expect(
            "07", "Left sequence ascends by a constant step",
            view.constant_step(left) is not None,
            note=f"first values {left[:6]}",
        )
        record.expect(
            "08", "Right sequence ascends by a constant step",
            view.constant_step(right) is not None,
            note=f"first values {right[:6]}",
        )

        if std.ENFORCE_SEQUENCE_START:
            record.expect(
                "09", f"Left sequence starts at {std.LEFT_SEQUENCE_START}",
                bool(left) and left[0] == std.LEFT_SEQUENCE_START,
                note=f"found {left[0] if left else 'none'}",
            )
        else:
            record.skip("09", "Sequence start value", "Not enforced by the site standard.")