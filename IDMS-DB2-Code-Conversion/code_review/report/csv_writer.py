"""Writes a ReviewResult as CSV.

write()         one row per criterion, for a single program
write_summary() one row per program, for a batch run

Presentation only. Headers come from code_review.standards.wording.
"""

from __future__ import annotations

import csv
from pathlib import Path

from code_review.engine.models import ReviewResult
from code_review.engine.reviewer import is_accepted
from code_review.standards import wording as w

TEXT_ENCODING = "utf-8"
FILE_SUFFIX = ".csv"


def rows(result: ReviewResult) -> list[list[str]]:
    """One row per criterion."""
    when = result.reviewed_at.strftime(w.CSV_TIMESTAMP_FORMAT)
    out: list[list[str]] = []
    for check in result.checks:
        for crit in check.criteria:
            out.append([
                result.program_name,
                when,
                result.source_file,
                check.check_id,
                check.severity,
                check.title,
                crit.criterion_id,
                crit.description,
                crit.outcome.value,
                crit.note,
                w.CSV_LINE_SEPARATOR.join(
                    str(f.line_number)
                    for f in crit.findings
                    if f.line_number
                ),
            ])
    return out


def summary_rows(results: list[ReviewResult]) -> list[list[str]]:
    """One row per reviewed program."""
    out: list[list[str]] = []
    for result in results:
        out.append([
            result.program_name,
            result.program_kind,
            result.reviewed_at.strftime(w.CSV_TIMESTAMP_FORMAT),
            result.source_file,
            result.passed,
            result.failed,
            result.skipped,
            result.blocked,
            w.ACCEPTED if is_accepted(result) else w.REJECTED,
        ])
    return out


def write(result: ReviewResult, folder: Path, stem: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = Path(folder) / f"{stem}{FILE_SUFFIX}"
    with path.open("w", newline="", encoding=TEXT_ENCODING) as handle:
        writer = csv.writer(handle)
        writer.writerow(w.CSV_HEADER)
        writer.writerows(rows(result))
    return path


def write_summary(
    results: list[ReviewResult],
    folder: Path,
    stem: str,
) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = Path(folder) / f"{stem}{FILE_SUFFIX}"
    with path.open("w", newline="", encoding=TEXT_ENCODING) as handle:
        writer = csv.writer(handle)
        writer.writerow(w.CSV_SUMMARY_HEADER)
        writer.writerows(summary_rows(results))
    return path