"""Code review result models. Data only.

No file access, no printing, no wording. Every counter the report needs is
derived here so writers stay presentation-only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Outcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"


# Severity of an outcome when several must be reduced to one.
_RANK = {
    Outcome.PASS: 0,
    Outcome.SKIPPED: 1,
    Outcome.BLOCKED: 2,
    Outcome.FAIL: 3,
}


def worst(items: list[Outcome]) -> Outcome:
    """Strict reduction: the most severe outcome in the list.

    Kept for callers that genuinely want strictness. CheckResult.outcome
    deliberately does NOT use this, because an informational SKIPPED must
    not mask passing criteria.
    """
    return max(items, key=lambda o: _RANK[o]) if items else Outcome.SKIPPED


@dataclass
class Finding:
    line_number: int = 0
    text: str = ""
    message: str = ""

    def render(self) -> str:
        if self.line_number:
            return f"line {self.line_number:>5} : {self.text}"
        return self.text or self.message


@dataclass
class Criterion:
    criterion_id: str
    description: str
    outcome: Outcome
    note: str = ""
    findings: list[Finding] = field(default_factory=list)


@dataclass
class CheckResult:
    check_id: str
    title: str
    severity: str
    criteria: list[Criterion] = field(default_factory=list)

    @property
    def outcome(self) -> Outcome:
        """A check is SKIPPED only when nothing was actually scored.

        Precedence: FAIL, then BLOCKED, then PASS, then SKIPPED.

        A check with eight passing criteria and one informational skip is
        a PASS. Ranking SKIPPED above PASS made the report under-state
        quality, because a site standard that is deliberately not enforced
        turned a whole check grey.
        """
        outcomes = [c.outcome for c in self.criteria]
        if not outcomes:
            return Outcome.SKIPPED
        if Outcome.FAIL in outcomes:
            return Outcome.FAIL
        if Outcome.BLOCKED in outcomes:
            return Outcome.BLOCKED
        if Outcome.PASS in outcomes:
            return Outcome.PASS
        return Outcome.SKIPPED

    def _count(self, outcome: Outcome) -> int:
        return sum(1 for c in self.criteria if c.outcome is outcome)

    @property
    def passed(self) -> int:
        return self._count(Outcome.PASS)

    @property
    def failed(self) -> int:
        return self._count(Outcome.FAIL)

    @property
    def skipped(self) -> int:
        return self._count(Outcome.SKIPPED)

    @property
    def blocked(self) -> int:
        return self._count(Outcome.BLOCKED)

    @property
    def total(self) -> int:
        return len(self.criteria)

    @property
    def failures(self) -> list[Criterion]:
        return [c for c in self.criteria if c.outcome is Outcome.FAIL]

    @property
    def skips(self) -> list[Criterion]:
        return [c for c in self.criteria if c.outcome is Outcome.SKIPPED]

    @property
    def note(self) -> str:
        for c in self.criteria:
            if c.note:
                return c.note
        return ""


@dataclass
class ReviewResult:
    program_name: str = ""
    program_kind: str = ""
    source_file: str = ""
    reviewed_at: datetime = field(default_factory=datetime.now)
    checks: list[CheckResult] = field(default_factory=list)

    # ---- check level -------------------------------------------------
    def _by(self, outcome: Outcome) -> list[CheckResult]:
        return [c for c in self.checks if c.outcome is outcome]

    @property
    def total(self) -> int:
        return len(self.checks)

    @property
    def passed(self) -> int:
        return len(self._by(Outcome.PASS))

    @property
    def failed(self) -> int:
        return len(self._by(Outcome.FAIL))

    @property
    def skipped(self) -> int:
        return len(self._by(Outcome.SKIPPED))

    @property
    def blocked(self) -> int:
        return len(self._by(Outcome.BLOCKED))

    @property
    def failed_checks(self) -> list[CheckResult]:
        return self._by(Outcome.FAIL)

    def failed_at(self, severity: str) -> list[CheckResult]:
        s = str(severity or "").upper()
        return [c for c in self.failed_checks if c.severity.upper() == s]

    # ---- criterion level ---------------------------------------------
    @property
    def criteria_passed(self) -> int:
        return sum(c.passed for c in self.checks)

    @property
    def criteria_failed(self) -> int:
        return sum(c.failed for c in self.checks)

    @property
    def criteria_skipped(self) -> int:
        return sum(c.skipped for c in self.checks)

    @property
    def criteria_blocked(self) -> int:
        return sum(c.blocked for c in self.checks)

    @property
    def criteria_total(self) -> int:
        return sum(c.total for c in self.checks)