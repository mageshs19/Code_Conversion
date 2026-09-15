# LOCATION: src/idms_db2_phase2/testing/execution/orchestrator.py
# ACTION: CREATE NEW FILE

"""Batch orchestrator: selects steps, runs them, reports the outcome."""

from __future__ import annotations

from idms_db2_phase2.testing.batch_console import BatchConsole
from idms_db2_phase2.testing.execution.models import (
    BatchOutcome,
    BatchStep,
    StepOutcome,
)
from idms_db2_phase2.testing.execution.output_reader import OutputReader
from idms_db2_phase2.testing.execution.report_renderer import ReportRenderer
from idms_db2_phase2.testing.execution.step_runner import StepRunner
from rules.batch_console_rules import (
    EXIT_ERROR,
    EXIT_OK,
    EXIT_REJECTED,
    MODE_ALL,
    MODES,
    VALUE_UNKNOWN,
)


class BatchExecution:
    """Runs conversion and code review as one reported batch."""

    def __init__(
        self,
        mode: str = MODE_ALL,
        review: bool = True,
        quiet: bool = False,
    ) -> None:
        self.mode = mode if mode in MODES else MODE_ALL
        self.review = review

        self.console = BatchConsole(quiet=quiet)
        self.reader = OutputReader()
        self.runner = StepRunner(console=self.console, reader=self.reader)
        self.renderer = ReportRenderer(
            console=self.console, reader=self.reader
        )
        self.outcome = BatchOutcome()

    # =================================================================
    # Public entry point
    # =================================================================
    def run(self) -> int:
        self.console.banner()
        self.renderer.inputs(self.mode)

        self._execute()

        self.renderer.metadata(self.outcome)
        self.renderer.summary(self.outcome)
        self.renderer.artefacts(self.outcome)
        self.renderer.failures(self.outcome)
        self.renderer.verdict(self.outcome)
        self.console.closing()

        return self._exit_code()

    # =================================================================
    # Execution
    # =================================================================
    def selected_steps(self) -> list[BatchStep]:
        """Steps that will actually run, in order.

        Scope is applied HERE rather than inside the loop, so the step
        counter reflects the work being done. Listing four steps and
        marking two SKIPPED told the reader nothing and made [2/4] a lie.
        """
        return [
            step
            for step in BatchStep.declared()
            if (self.review or not step.is_review) and step.in_scope(self.mode)
        ]

    def _execute(self) -> None:
        self.renderer.execution_header()

        steps = self.selected_steps()
        total = len(steps)

        for index, step in enumerate(steps, start=1):
            outcome = self.runner.run(index, total, step)
            self.outcome.steps.append(outcome)
            self._absorb(outcome)

        self.renderer.execution_footer()

    # =================================================================
    # Metadata harvesting
    # =================================================================
    def _absorb(self, outcome: StepOutcome) -> None:
        """Keep the first value any runner reported."""
        text = outcome.stdout or ""
        if not text:
            return

        if self.outcome.mapping_rows == VALUE_UNKNOWN:
            self.outcome.mapping_rows = self.reader.mapping_rows(text)

        if self.outcome.dclgen_columns == VALUE_UNKNOWN:
            self.outcome.dclgen_columns = self.reader.dclgen_columns(text)

        if self.outcome.copybook_fields == VALUE_UNKNOWN:
            self.outcome.copybook_fields = self.reader.copybook_fields(text)

        if not self.outcome.report_folder:
            self.outcome.report_folder = self.reader.report_folder(text)

    # =================================================================
    # Exit code
    # =================================================================
    def _exit_code(self) -> int:
        if self.outcome.errors:
            return EXIT_ERROR
        if self.outcome.failures:
            return EXIT_REJECTED
        return EXIT_OK