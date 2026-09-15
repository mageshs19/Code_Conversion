"""Automated code review of generated DB2 COBOL.

Reads a converted .cbl, scores it against the site COBOL and DB2 standards,
and produces a Code Review Report.

Dependency direction is one-way: this package reads from the converter;
the converter never imports from here.
"""

from code_review.engine import (
    CheckResult, Outcome, ReviewContext, ReviewResult, Reviewer,
    blockers, is_accepted,
)

__all__ = [
    "ReviewContext", "Reviewer", "ReviewResult", "CheckResult",
    "Outcome", "is_accepted", "blockers",
]