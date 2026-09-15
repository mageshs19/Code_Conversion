"""Renders a ReviewResult as the human-readable Code Review Report.

Presentation only. Every string comes from code_review.standards.wording
and every number comes from code_review.engine.models.
"""

from __future__ import annotations

from pathlib import Path

from code_review.engine.models import Outcome, ReviewResult
from code_review.engine.reviewer import blockers, is_accepted
from code_review.standards import wording as w

TEXT_ENCODING = "utf-8"
FILE_SUFFIX = ".txt"


def render(result: ReviewResult) -> str:
    out: list[str] = []
    add = out.append

    # ---- header ------------------------------------------------------
    add(w.REPORT_TITLE)
    add(w.RULE)
    add(w.F_PROGRAM.format(value=result.program_name or w.VALUE_UNNAMED))
    add(w.F_KIND.format(value=result.program_kind or w.VALUE_UNKNOWN))
    add(w.F_SOURCE.format(value=result.source_file or w.VALUE_IN_MEMORY))
    add(w.F_WHEN.format(
        value=result.reviewed_at.strftime(w.CSV_TIMESTAMP_FORMAT),
    ))
    add(w.F_TOTALS.format(
        passed=result.passed,
        failed=result.failed,
        skipped=result.skipped,
        blocked=result.blocked,
    ))
    add(w.F_CRITERIA.format(
        passed=result.criteria_passed,
        failed=result.criteria_failed,
        skipped=result.criteria_skipped,
        blocked=result.criteria_blocked,
    ))
    add(w.F_RESULT.format(
        value=w.ACCEPTED if is_accepted(result) else w.REJECTED,
    ))

    blocking = blockers(result)
    if blocking:
        add(w.F_BLOCKING.format(
            value=", ".join(c.check_id for c in blocking),
        ))

    # ---- detail ------------------------------------------------------
    add("")
    add(w.H_DETAIL)
    add(w.RULE)

    for check in result.checks:
        add(w.F_CHECK.format(
            symbol=w.SYMBOL[check.outcome.value],
            check_id=check.check_id,
            severity=check.severity,
            title=check.title,
        ))
        for crit in check.criteria:
            if crit.outcome is Outcome.PASS:
                continue
            add(w.F_CRIT.format(
                criterion_id=crit.criterion_id,
                description=crit.description,
            ))
            if crit.note:
                add(w.F_NOTE.format(note=crit.note))
            for finding in crit.findings:
                add(w.F_FIND.format(finding=finding.render()))

    # ---- failures ----------------------------------------------------
    add("")
    add(w.H_FAILURES)
    add(w.RULE)

    failed = result.failed_checks
    if not failed:
        add(w.NO_FAILURES)
    else:
        for check in failed:
            add(w.F_FAIL_CHECK.format(
                check_id=check.check_id,
                severity=check.severity,
                title=check.title,
            ))
            for crit in check.failures:
                add(w.F_FAIL_CRIT.format(
                    criterion_id=crit.criterion_id,
                    description=crit.description,
                ))
                if crit.note:
                    add(w.F_FAIL_NOTE.format(note=crit.note))

    add("")
    return "\n".join(out)


def write(result: ReviewResult, folder: Path, stem: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = Path(folder) / f"{stem}{FILE_SUFFIX}"
    path.write_text(render(result), encoding=TEXT_ENCODING)
    return path