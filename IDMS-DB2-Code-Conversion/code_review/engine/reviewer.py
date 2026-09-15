"""Runs the check pipeline against one ReviewContext."""

from __future__ import annotations

from code_review.engine.check_base import Check, Recorder
from code_review.engine.cobol_view import CobolView
from code_review.engine.context import ReviewContext
from code_review.engine.models import CheckResult, Criterion, Outcome, ReviewResult
from code_review.engine.registry import load_checks

try:
    from code_review.standards.pipeline import BLOCKING_SEVERITIES, EVIDENCE_LIMIT
except ImportError:
    BLOCKING_SEVERITIES, EVIDENCE_LIMIT = ("Critical",), 10


class Reviewer:
    def __init__(self, checks: list[Check] | None = None) -> None:
        self.checks = checks if checks is not None else load_checks()

    def review(self, ctx: ReviewContext) -> ReviewResult:
        view = CobolView(ctx.converted_cobol)
        result = ReviewResult(
            program_name=ctx.program_name,
            program_kind=ctx.program_kind,
            source_file=ctx.source_file,
        )
        for check in self.checks:
            result.checks.append(self._one(check, ctx, view))
        return result

    def _one(self, check: Check, ctx: ReviewContext, view: CobolView) -> CheckResult:
        out = CheckResult(check.CHECK_ID, check.TITLE, check.SEVERITY)

        def single(outcome: Outcome, note: str) -> CheckResult:
            out.criteria.append(
                Criterion(f"{check.CHECK_ID}.00", check.TITLE, outcome, note=note)
            )
            return out

        if not check.applies(ctx):
            return single(Outcome.SKIPPED, f"Applies to {check.APPLIES_TO} programs only.")

        missing = ctx.missing(check.NEEDS)
        if missing:
            return single(Outcome.BLOCKED, "Not supplied: " + ", ".join(missing))

        if view.is_empty:
            return single(Outcome.BLOCKED, "Converted COBOL is empty.")

        try:
            if not check.relevant(ctx, view):
                return single(Outcome.SKIPPED, check.not_relevant_reason())
            recorder = Recorder(check.CHECK_ID, limit=EVIDENCE_LIMIT)
            check.review(ctx, view, recorder)
            out.criteria.extend(recorder.criteria)
        except Exception as exc:  # noqa: BLE001
            return single(Outcome.BLOCKED, f"Check raised an error: {exc}")

        if not out.criteria:
            return single(Outcome.SKIPPED, "No criteria recorded.")
        return out


def is_accepted(result: ReviewResult) -> bool:
    return not any(result.failed_at(s) for s in BLOCKING_SEVERITIES)


def blockers(result: ReviewResult) -> list[CheckResult]:
    seen = {}
    for severity in BLOCKING_SEVERITIES:
        for check in result.failed_at(severity):
            seen[check.check_id] = check
    return [seen[k] for k in sorted(seen)]