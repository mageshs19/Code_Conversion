"""Base class and recorder for a single code review check."""

from __future__ import annotations

from code_review.engine.cobol_view import CobolView, Line
from code_review.engine.context import ReviewContext
from code_review.engine.models import Criterion, Finding, Outcome

CRITICAL = "Critical"
MAJOR = "Major"
MINOR = "Minor"

BOTH = "BOTH"
RETRIEVAL = "RETRIEVAL"
UPDATE = "UPDATE"


def _finding(item) -> Finding:
    if isinstance(item, Line):
        return Finding(line_number=item.number, text=item.body.rstrip())
    if isinstance(item, Finding):
        return item
    return Finding(text=str(item))


class Recorder:
    """Collects criterion outcomes for one check."""

    def __init__(self, check_id: str, limit: int = 10) -> None:
        self.check_id = check_id
        self.limit = limit
        self.criteria: list[Criterion] = []

    def _add(self, num, desc, outcome, note="", findings=None) -> None:
        self.criteria.append(
            Criterion(
                criterion_id=f"{self.check_id}.{num}",
                description=desc,
                outcome=outcome,
                note=note,
                findings=[_finding(f) for f in list(findings or [])[: self.limit]],
            )
        )

    def ok(self, num, desc) -> None:
        self._add(num, desc, Outcome.PASS)

    def fail(self, num, desc, note="", findings=None) -> None:
        self._add(num, desc, Outcome.FAIL, note=note, findings=findings)

    def skip(self, num, desc, reason="") -> None:
        self._add(num, desc, Outcome.SKIPPED, note=reason)

    def expect(self, num, desc, condition, note="", findings=None) -> None:
        if condition:
            self.ok(num, desc)
        else:
            self.fail(num, desc, note=note, findings=findings)

    def expect_none(self, num, desc, offenders, note="") -> None:
        items = list(offenders or [])
        self.expect(
            num, desc,
            condition=not items,
            note=note or f"{len(items)} occurrence(s)",
            findings=items,
        )

    def expect_all(self, num, desc, missing, note="") -> None:
        items = list(missing or [])
        self.expect(
            num, desc,
            condition=not items,
            note=note or ("missing: " + ", ".join(str(i) for i in items[:10])),
            findings=items,
        )


class Check:
    """Base class for every code review check."""

    CHECK_ID: str = ""
    TITLE: str = ""
    SEVERITY: str = MAJOR
    APPLIES_TO: str = BOTH
    NEEDS: tuple[str, ...] = ("converted_cobol",)
    ORDER: int = 0

    def applies(self, ctx: ReviewContext) -> bool:
        scope = str(self.APPLIES_TO).upper()
        return scope == BOTH or scope == str(ctx.program_kind).upper()

    def relevant(self, ctx: ReviewContext, view: CobolView) -> bool:
        """Override when the check only makes sense for some programs."""
        return True

    def not_relevant_reason(self) -> str:
        return "Program does not contain the construct this check inspects."

    def review(self, ctx: ReviewContext, view: CobolView, record: Recorder) -> None:
        raise NotImplementedError