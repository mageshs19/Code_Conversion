# LOCATION: src/idms_db2_phase2/testing/execution/report_renderer.py
# ACTION: CREATE NEW FILE

"""Renders every batch section through BatchConsole.

Presentation orchestration only: decides WHAT appears in each section,
while BatchConsole decides HOW a line is drawn.
"""

from __future__ import annotations

from idms_db2_phase2.testing.execution.environment import PROJECT_ROOT
from idms_db2_phase2.testing.execution.input_inspector import InputInspector
from idms_db2_phase2.testing.execution.models import BatchOutcome
from idms_db2_phase2.testing.execution.output_reader import OutputReader
from rules.batch_console_rules import (
    DEFAULT_REPORT_FOLDER,
    LABEL_COPYBOOK,
    LABEL_COPYBOOK_FIELDS,
    LABEL_DCLGEN,
    LABEL_DCLGEN_COLUMNS,
    LABEL_LOG_FOLDER,
    LABEL_MAPPING_ROWS,
    LABEL_MAPPING_SHEET,
    LABEL_MODE,
    LABEL_OUTPUT_FOLDER,
    LABEL_REPORT_FOLDER,
    LABEL_RETRIEVAL_PROGRAMS,
    LABEL_UPDATE_PROGRAMS,
    MSG_DETAIL_HEADER,
    MSG_HINT_REPORTS,
    MSG_NO_DETAIL,
    SECTION_ARTEFACTS,
    SECTION_EXECUTION,
    SECTION_INPUTS,
    SECTION_METADATA,
    SECTION_SUMMARY,
)


class ReportRenderer:
    """Builds the on-screen batch report."""

    def __init__(
        self,
        console,
        inspector: InputInspector | None = None,
        reader: OutputReader | None = None,
    ) -> None:
        self.console = console
        self.inspector = inspector or InputInspector()
        self.reader = reader or OutputReader()

    # =================================================================
    # Sections
    # =================================================================
    def inputs(self, mode: str) -> None:
        self.console.section(SECTION_INPUTS)
        self.console.key_value(LABEL_MODE, mode)

        counts = self.inspector.counts()
        self.console.file_count(LABEL_MAPPING_SHEET, counts["mapping"])
        self.console.file_count(LABEL_DCLGEN, counts["dclgen"])
        self.console.file_count(LABEL_COPYBOOK, counts["copybook"])
        self.console.key_value(LABEL_RETRIEVAL_PROGRAMS, counts["retrieval"])
        self.console.key_value(LABEL_UPDATE_PROGRAMS, counts["update"])
        self.console.blank()

    def execution_header(self) -> None:
        self.console.section(SECTION_EXECUTION)

    def execution_footer(self) -> None:
        self.console.blank()

    def metadata(self, outcome: BatchOutcome) -> None:
        if not outcome.has_metadata:
            return

        self.console.section(SECTION_METADATA)
        self.console.key_value(LABEL_MAPPING_ROWS, outcome.mapping_rows)
        self.console.key_value(LABEL_DCLGEN_COLUMNS, outcome.dclgen_columns)
        self.console.key_value(LABEL_COPYBOOK_FIELDS, outcome.copybook_fields)
        self.console.blank()

    def summary(self, outcome: BatchOutcome) -> None:
        self.console.section(SECTION_SUMMARY)
        self.console.summary_header()

        for step in outcome.steps:
            self.console.summary_row(step.label, step.status, step.seconds)

        self.console.summary_total(outcome.seconds, outcome.failures)
        self.console.blank()

    def artefacts(self, outcome: BatchOutcome) -> None:
        output_folder, logs_folder = self.inspector.folders()
        report_folder = outcome.report_folder or str(
            PROJECT_ROOT / DEFAULT_REPORT_FOLDER
        )

        self.console.section(SECTION_ARTEFACTS)
        self.console.key_value(LABEL_OUTPUT_FOLDER, output_folder)
        self.console.key_value(LABEL_REPORT_FOLDER, report_folder)
        self.console.key_value(LABEL_LOG_FOLDER, logs_folder)

    def failures(self, outcome: BatchOutcome) -> None:
        failing = outcome.failing_steps
        if not failing:
            return

        lines: list[str] = []

        for step in failing:
            lines.append(f"{step.label}: {step.status}")

            detail = self.reader.failure_lines(step.combined_output)
            if detail:
                lines.extend(f"  {entry}" for entry in detail)
            else:
                lines.append(f"  {MSG_NO_DETAIL}")

            lines.append("")

        lines.append(MSG_HINT_REPORTS)
        self.console.detail(MSG_DETAIL_HEADER, "\n".join(lines))

    def verdict(self, outcome: BatchOutcome) -> None:
        self.console.verdict(outcome.failures)