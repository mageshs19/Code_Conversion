from __future__ import annotations

from dataclasses import dataclass, field

from idms_db2_phase2.services.name_normalizer import NameNormalizer


@dataclass
class ParagraphSpan:
    name: str
    start_line: int
    end_line: int
    lines: list[str] = field(default_factory=list)


@dataclass
class CursorLoop:
    record_name: str = ""
    set_name: str = ""
    operation: str = ""
    operation_line: int = 0
    process_paragraph: str = ""
    perform_line: int = 0
    until_line: int = 0
    loop_type: str = "unknown"
    cursor_name: str = ""
    open_paragraph: str = ""
    fetch_paragraph: str = ""
    close_paragraph: str = ""


@dataclass
class OutputWrite:
    output_record: str = ""
    paragraph_name: str = ""
    write_line: int = 0
    move_lines: list[str] = field(default_factory=list)


@dataclass
class DateUsage:
    host_field: str = ""
    dclgen_group: str = ""
    idms_record: str = ""
    line_number: int = 0
    line_text: str = ""
    usage_type: str = ""


@dataclass
class ProgramFlowAnalysis:
    paragraphs: list[ParagraphSpan] = field(default_factory=list)
    cursor_loops: list[CursorLoop] = field(default_factory=list)
    output_writes: list[OutputWrite] = field(default_factory=list)
    date_usages: list[DateUsage] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)

    def process_paragraph_for_cursor(
        self,
        cursor_name: str,
    ) -> str:
        cursor = NameNormalizer.to_cobol(NameNormalizer.normalize(cursor_name))

        for loop in self.cursor_loops:
            loop_cursor = NameNormalizer.to_cobol(
                NameNormalizer.normalize(loop.cursor_name)
            )

            if loop_cursor == cursor:
                return loop.process_paragraph

        return ""

    def loop_for_set(
        self,
        set_name: str,
    ) -> CursorLoop | None:
        target = NameNormalizer.normalize(set_name)

        for loop in self.cursor_loops:
            if NameNormalizer.normalize(loop.set_name) == target:
                return loop

        return None

    def loop_for_record(
        self,
        record_name: str,
    ) -> CursorLoop | None:
        target = NameNormalizer.normalize(record_name)

        for loop in self.cursor_loops:
            if NameNormalizer.normalize(loop.record_name) == target:
                return loop

        return None