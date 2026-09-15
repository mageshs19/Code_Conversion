# LOCATION: src/idms_db2_phase2/testing/execution/step_runner.py
# ACTION: CREATE NEW FILE

"""Runs one batch step as a subprocess.

Each runner is launched as its own process rather than imported:

  - a runner that calls sys.exit, as these do, would otherwise terminate
    the batch;
  - each runner performs its own sys.path bootstrap, which conflicts when
    several are imported into one interpreter;
  - a change inside a runner cannot break the batch, because the contract
    is the command line and the exit code, not a function signature.
"""

from __future__ import annotations

import subprocess
import sys
import time

from idms_db2_phase2.testing.execution.environment import (
    runner_path,
    subprocess_environment,
)
from idms_db2_phase2.testing.execution.models import BatchStep, StepOutcome
from idms_db2_phase2.testing.execution.output_reader import OutputReader
from idms_db2_phase2.testing.execution.environment import PROJECT_ROOT
from rules.batch_console_rules import (
    MSG_RUNNER_MISSING,
    REVIEW_QUIET_ARG,
    STATUS_FAILED,
    STEP_TIMEOUT_SECONDS,
)

TIMEOUT_NOTE_TEMPLATE = "exceeded {seconds}s"


class StepRunner:
    """Executes a single step and reports progress through the console."""

    def __init__(self, console, reader: OutputReader | None = None) -> None:
        self.console = console
        self.reader = reader or OutputReader()

    def run(self, index: int, total: int, step: BatchStep) -> StepOutcome:
        runner = runner_path(step.path)

        if not runner.exists():
            return self._failed(
                index,
                total,
                step,
                seconds=0.0,
                note=MSG_RUNNER_MISSING.format(path=step.path),
            )

        self.console.step_start(index, total, step.label)
        started = time.monotonic()

        try:
            completed = subprocess.run(
                self._command(runner, step.is_review),
                cwd=str(PROJECT_ROOT),
                env=subprocess_environment(),
                capture_output=True,
                text=True,
                timeout=STEP_TIMEOUT_SECONDS,
                check=False,
            )

        except subprocess.TimeoutExpired:
            return self._failed(
                index,
                total,
                step,
                seconds=time.monotonic() - started,
                note=TIMEOUT_NOTE_TEMPLATE.format(
                    seconds=STEP_TIMEOUT_SECONDS
                ),
            )

        except Exception as exc:  # noqa: BLE001
            return self._failed(
                index,
                total,
                step,
                seconds=time.monotonic() - started,
                note=str(exc),
            )

        seconds = time.monotonic() - started
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""

        status = self.reader.status_for(
            completed.returncode, stdout, step.is_review
        )
        note = self.reader.note_for(stdout, step.is_review)

        self.console.step_finish(
            index, total, step.label, status, seconds, note
        )

        return StepOutcome(
            key=step.key,
            label=step.label,
            status=status,
            seconds=seconds,
            note=note,
            stdout=stdout,
            stderr=stderr,
        )

    # =================================================================
    # Helpers
    # =================================================================
    @staticmethod
    def _command(runner, is_review: bool) -> list[str]:
        command = [sys.executable, str(runner)]
        if is_review:
            command.append(REVIEW_QUIET_ARG)
        return command

    def _failed(
        self,
        index: int,
        total: int,
        step: BatchStep,
        seconds: float,
        note: str,
    ) -> StepOutcome:
        self.console.step_finish(
            index, total, step.label, STATUS_FAILED, seconds, note
        )
        return StepOutcome(
            key=step.key,
            label=step.label,
            status=STATUS_FAILED,
            seconds=seconds,
            note=note,
        )