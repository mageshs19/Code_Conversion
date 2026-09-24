# LOCATION: src/idms_db2_phase2/testing/execution/step_runner.py
# ACTION: REPLACE ENTIRE FILE

"""Runs one batch step as a subprocess.

Each runner is launched as its own process rather than imported:

  - a runner that calls sys.exit, as these do, would otherwise terminate
    the batch;
  - each runner performs its own sys.path bootstrap, which conflicts when
    several are imported into one interpreter;
  - a change inside a runner cannot break the batch, because the contract
    is the command line and the exit code, not a function signature.

CORRECTION - the pipeline converted every program twice
-------------------------------------------------------
The command line was the ONLY contract, and it carried no artifact. A
review step was therefore told nothing about what the convert step before
it had produced, so `review_retrieval.py` / `review_update.py` - which are
END-TO-END runners, not review phases - re-ran the whole conversion to
obtain an input they could trust. Two conversions, two output files, and
the duplication was invisible because the orchestrator only ever compared
exit codes.

A review step is now handed `--folder <output dir>` and `--kind`, so it
reviews what the convert step wrote instead of producing its own copy.
The folder IS the contract the batch previously lacked.

This requires the review steps in rules/batch_console_rules.STEP_DEFINITIONS
to point at `code_review/runner/review_file.py`, which reviews only and
never converts. Steps whose key is absent from REVIEW_FOLDERS receive no
extra arguments, so a review runner that does not accept `--folder` is
never handed one.
"""

from __future__ import annotations

import subprocess
import sys
import time

from config.path_settings import (
    DEFAULT_RETRIEVAL_OUTPUT_DIR,
    DEFAULT_UPDATE_OUTPUT_DIR,
)
from idms_db2_phase2.testing.execution.environment import (
    PROJECT_ROOT,
    runner_path,
    subprocess_environment,
)
from idms_db2_phase2.testing.execution.models import BatchStep, StepOutcome
from idms_db2_phase2.testing.execution.output_reader import OutputReader
from rules.batch_console_rules import (
    MSG_RUNNER_MISSING,
    REVIEW_FOLDER_ARG,
    REVIEW_KIND_ARG,
    REVIEW_LATEST_ARG,
    REVIEW_QUIET_ARG,
    STATUS_FAILED,
    STEP_REVIEW_KIND,
    STEP_REVIEW_RETRIEVAL,
    STEP_REVIEW_UPDATE,
    STEP_TIMEOUT_SECONDS,
)

TIMEOUT_NOTE_TEMPLATE = "exceeded {seconds}s"

# The artifact each review step consumes. A step key that is not listed
# here is launched with no folder argument, so an end-to-end review runner
# keeps working unchanged.
REVIEW_FOLDERS = {
    STEP_REVIEW_RETRIEVAL: DEFAULT_RETRIEVAL_OUTPUT_DIR,
    STEP_REVIEW_UPDATE: DEFAULT_UPDATE_OUTPUT_DIR,
}


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
                self._command(runner, step),
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
    def _command(runner, step: BatchStep) -> list[str]:
        """Command line for one step.

        A review step is handed the output folder the convert step just
        wrote, plus --latest. Without --latest the reviewer scores every
        .cbl the folder has ever held, so a clean run was reported as
        "5 reviewed, 0 accepted, 5 rejected" on four stale files.
        """
        command = [sys.executable, str(runner)]

        if not step.is_review:
            return command

        command.append(REVIEW_QUIET_ARG)

        folder = REVIEW_FOLDERS.get(step.key)
        if folder is not None:
            command.extend([REVIEW_FOLDER_ARG, str(folder), REVIEW_LATEST_ARG])

        kind = STEP_REVIEW_KIND.get(step.key, "")
        if kind:
            command.extend([REVIEW_KIND_ARG, kind])

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


__all__ = ["StepRunner", "REVIEW_FOLDERS"]