"""CHK-03 No residual IDMS statements."""

from __future__ import annotations

from code_review.engine.check_base import CRITICAL, Check
from code_review.standards import cobol_standards as std


class ResidualIdmsCheck(Check):
    CHECK_ID = "CHK-03"
    TITLE = "No residual IDMS statements"
    SEVERITY = CRITICAL
    ORDER = 30

    def review(self, ctx, view, record):
        record.expect_none(
            "01", "No IDMS executable verbs remain",
            [l for l in view.code
             if l.logical.startswith(std.IDMS_EXECUTABLE_PREFIXES)],
        )
        record.expect_none(
            "02", "No IDMS declarative statements remain",
            [l for l in view.code
             if l.logical.startswith(std.IDMS_DECLARATIVE_PREFIXES)],
        )
        record.expect_none(
            "03", "No IDMS status or abort references remain",
            [l for l in view.code
             if any(t in l.logical for t in std.IDMS_TOKENS)],
        )
        record.expect_none(
            "04", "No USAGE-MODE clauses remain",
            [l for l in view.code
             if any(c in l.logical for c in std.IDMS_CLAUSES)],
        )