from __future__ import annotations

from idms_db2_phase2.domain.models import DclgenColumn, IdmsOperation, SheetMappingRow
from idms_db2_phase2.resolvers.cursor_name_resolver import CursorNameResolver
from idms_db2_phase2.services.program_cursor_loop_analyzer import (
    ProgramCursorLoopAnalyzer,
)
from idms_db2_phase2.services.program_date_usage_analyzer import (
    ProgramDateUsageAnalyzer,
)
from idms_db2_phase2.services.program_flow_line_collector import (
    ProgramFlowLineCollector,
)
from idms_db2_phase2.services.program_flow_models import (
    CursorLoop,
    DateUsage,
    OutputWrite,
    ParagraphSpan,
    ProgramFlowAnalysis,
)
from idms_db2_phase2.services.program_output_write_analyzer import (
    ProgramOutputWriteAnalyzer,
)
from idms_db2_phase2.services.program_paragraph_analyzer import (
    ProgramParagraphAnalyzer,
)


class ProgramFlowAnalyzer:
    """
    Generic flow analyzer for diagnostics.

    This analyzer does not rewrite COBOL. It detects:
    - procedure paragraphs
    - cursor-like operations from parsed IDMS operations
    - output write statements
    - basic date usage hints
    """

    def __init__(
        self,
        mapping_rows: list[SheetMappingRow] | None = None,
        dclgen_columns: list[DclgenColumn] | None = None,
    ) -> None:
        self.mapping_rows = mapping_rows or []
        self.dclgen_columns = dclgen_columns or []

        self.cursor_name_resolver = CursorNameResolver()
        self.line_collector = ProgramFlowLineCollector()
        self.paragraph_analyzer = ProgramParagraphAnalyzer()
        self.cursor_loop_analyzer = ProgramCursorLoopAnalyzer(
            cursor_name_resolver=self.cursor_name_resolver,
        )
        self.output_write_analyzer = ProgramOutputWriteAnalyzer(
            paragraph_analyzer=self.paragraph_analyzer,
        )
        self.date_usage_analyzer = ProgramDateUsageAnalyzer()

    def analyze(
        self,
        cobol_text: str,
        operations: list[IdmsOperation] | None = None,
    ) -> ProgramFlowAnalysis:
        if not str(cobol_text or "").strip():
            return ProgramFlowAnalysis(
                diagnostics=["Program flow analyzer: COBOL text is empty."]
            )

        logical_lines = self.line_collector.logical_lines_with_numbers(cobol_text)
        paragraphs = self.paragraph_analyzer.paragraph_spans(logical_lines)
        cursor_loops = self.cursor_loop_analyzer.cursor_loops(operations or [])
        output_writes = self.output_write_analyzer.output_writes(
            logical_lines=logical_lines,
            paragraphs=paragraphs,
        )
        date_usages = self.date_usage_analyzer.date_usages(logical_lines)

        diagnostics = self._diagnostics(
            paragraphs=paragraphs,
            cursor_loops=cursor_loops,
            output_writes=output_writes,
            date_usages=date_usages,
        )

        return ProgramFlowAnalysis(
            paragraphs=paragraphs,
            cursor_loops=cursor_loops,
            output_writes=output_writes,
            date_usages=date_usages,
            diagnostics=diagnostics,
        )

    def _diagnostics(
        self,
        *,
        paragraphs: list[ParagraphSpan],
        cursor_loops: list[CursorLoop],
        output_writes: list[OutputWrite],
        date_usages: list[DateUsage],
    ) -> list[str]:
        diagnostics: list[str] = []

        diagnostics.append(
            f"Program flow analyzer: Sheet Mapping rows received: {len(self.mapping_rows)}"
        )
        diagnostics.append(
            f"Program flow analyzer: DCLGEN columns received: {len(self.dclgen_columns)}"
        )
        diagnostics.append(
            f"Program flow analyzer: paragraphs detected: {len(paragraphs)}"
        )
        diagnostics.append(
            f"Program flow analyzer: cursor loops detected: {len(cursor_loops)}"
        )
        diagnostics.append(
            f"Program flow analyzer: output writes detected: {len(output_writes)}"
        )
        diagnostics.append(
            f"Program flow analyzer: DB2 date usages detected: {len(date_usages)}"
        )

        for loop in cursor_loops[:5]:
            diagnostics.append(
                "Program flow analyzer: loop sample: "
                f"record={loop.record_name}, set={loop.set_name}, "
                f"type={loop.loop_type}, cursor={loop.cursor_name}"
            )

        return diagnostics


__all__ = [
    "DateUsage",
    "CursorLoop",
    "OutputWrite",
    "ParagraphSpan",
    "ProgramFlowAnalysis",
    "ProgramFlowAnalyzer",
]