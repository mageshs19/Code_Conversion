# LOCATION: src/idms_db2_phase2/testing/execution/models.py
# ACTION: CREATE NEW FILE

"""Batch execution data models. Data only, no behaviour beyond derivation."""

from __future__ import annotations

from dataclasses import dataclass, field

from rules.batch_console_rules import (
    FAILING_STATUSES,
    MODE_ALL,
    MODE_RETRIEVAL,
    MODE_UPDATE,
    STATUS_FAILED,
    STEP_CONVERT_RETRIEVAL,
    STEP_CONVERT_UPDATE,
    STEP_DEFINITIONS,
    STEP_REVIEW_RETRIEVAL,
    STEP_REVIEW_UPDATE,
    VALUE_UNKNOWN,
)

RETRIEVAL_STEPS = (STEP_CONVERT_RETRIEVAL, STEP_REVIEW_RETRIEVAL)
UPDATE_STEPS = (STEP_CONVERT_UPDATE, STEP_REVIEW_UPDATE)


@dataclass(frozen=True)
class BatchStep:
    """One declared step, before it runs."""

    key: str
    label: str
    path: str
    is_review: bool

    def in_scope(self, mode: str) -> bool:
        if mode == MODE_ALL:
            return True
        if mode == MODE_RETRIEVAL:
            return self.key in RETRIEVAL_STEPS
        if mode == MODE_UPDATE:
            return self.key in UPDATE_STEPS
        return True

    @classmethod
    def declared(cls) -> list["BatchStep"]:
        return [
            cls(key=key, label=label, path=path, is_review=is_review)
            for key, label, path, is_review in STEP_DEFINITIONS
        ]


@dataclass
class StepOutcome:
    """One executed step."""

    key: str
    label: str
    status: str
    seconds: float = 0.0
    note: str = ""
    stdout: str = ""
    stderr: str = ""

    @property
    def is_failure(self) -> bool:
        return self.status in FAILING_STATUSES

    @property
    def is_error(self) -> bool:
        return self.status == STATUS_FAILED

    @property
    def combined_output(self) -> str:
        return f"{self.stdout or ''}\n{self.stderr or ''}"


@dataclass
class BatchOutcome:
    """Everything the summary needs."""

    steps: list[StepOutcome] = field(default_factory=list)
    mapping_rows: str = VALUE_UNKNOWN
    dclgen_columns: str = VALUE_UNKNOWN
    copybook_fields: str = VALUE_UNKNOWN
    report_folder: str = ""

    @property
    def failures(self) -> int:
        return sum(1 for step in self.steps if step.is_failure)

    @property
    def errors(self) -> int:
        return sum(1 for step in self.steps if step.is_error)

    @property
    def seconds(self) -> float:
        return sum(step.seconds for step in self.steps)

    @property
    def failing_steps(self) -> list[StepOutcome]:
        return [step for step in self.steps if step.is_failure]

    @property
    def has_metadata(self) -> bool:
        return any(
            value != VALUE_UNKNOWN
            for value in (
                self.mapping_rows,
                self.dclgen_columns,
                self.copybook_fields,
            )
        )