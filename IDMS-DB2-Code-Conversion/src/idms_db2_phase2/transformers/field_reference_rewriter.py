from __future__ import annotations

from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.transformers.field_reference_context_builder import (
    FieldReferenceContextBuilder,
)
from idms_db2_phase2.transformers.field_reference_line_utils import (
    FieldReferenceLineUtils,
)
from idms_db2_phase2.transformers.field_reference_record_context import (
    FieldReferenceRecordContext,
)
from idms_db2_phase2.transformers.field_reference_replacement_engine import (
    FieldReferenceReplacementEngine,
)
from patterns.field_reference_rewriter_patterns import (
    DIVISION_PATTERN,
    END_EXEC_PATTERN,
    EXEC_SQL_PATTERN,
)


class FieldReferenceRewriter:
    """
    Generic IDMS field reference to DB2 DCLGEN reference rewriter.

    Public facade preserved for existing callers.

    Rules:
    - Qualified references are always eligible:
        FIELD OF RECORD
        FIELD IN RECORD
    - Bare references are eligible only when active record context is strong.
    - Date fields are protected only for bare references.
    """

    def __init__(
        self,
        mapping_repository: MappingRepository,
        table_name_resolver: TableNameResolver,
        host_variable_resolver: HostVariableResolver,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.table_name_resolver = table_name_resolver
        self.host_variable_resolver = host_variable_resolver

        self.rewrite_messages: list[str] = []
        self.messages: list[str] = self.rewrite_messages

        self.record_field_map: dict[str, dict[str, str]] = {}
        self.record_group_map: dict[str, str] = {}
        self.table_record_map: dict[str, str] = {}
        self.group_record_map: dict[str, str] = {}

        self.line_utils = FieldReferenceLineUtils()
        self.context_builder = FieldReferenceContextBuilder(
            mapping_repository=mapping_repository,
            table_name_resolver=table_name_resolver,
            host_variable_resolver=host_variable_resolver,
        )

    def rewrite(
        self,
        text: str,
    ) -> str:
        self.rewrite_messages = []
        self.messages = self.rewrite_messages

        if not text:
            return ""

        self._build_reference_maps()

        if not self.record_field_map:
            return str(text or "").rstrip() + "\n"

        lines = str(text or "").splitlines()

        has_any_division = any(
            DIVISION_PATTERN.match(self.line_utils.logical_line(line))
            for line in lines
        )

        record_context = FieldReferenceRecordContext(
            record_field_map=self.record_field_map,
            group_record_map=self.group_record_map,
        )

        replacement_engine = FieldReferenceReplacementEngine(
            record_field_map=self.record_field_map,
            rewrite_messages=self.rewrite_messages,
        )

        output_lines: list[str] = []
        inside_exec_sql = False

        current_division = "PROCEDURE" if not has_any_division else ""
        active_record = ""

        for raw_line in lines:
            line = raw_line.rstrip()
            logical = self.line_utils.logical_line(line)

            division_match = DIVISION_PATTERN.match(logical)

            if division_match:
                current_division = division_match.group(1).upper()
                active_record = ""
                output_lines.append(line)
                continue

            detected_context = record_context.detect_active_record_from_line(
                logical_line=logical,
                current_active_record=active_record,
            )

            if detected_context:
                active_record = detected_context

            if EXEC_SQL_PATTERN.match(logical):
                inside_exec_sql = True
                output_lines.append(line)
                continue

            if inside_exec_sql:
                output_lines.append(line)

                if END_EXEC_PATTERN.match(logical):
                    inside_exec_sql = False

                continue

            output_lines.append(
                self._rewrite_line(
                    line=line,
                    current_division=current_division,
                    active_record=active_record,
                    replacement_engine=replacement_engine,
                )
            )

        return "\n".join(output_lines).rstrip() + "\n"

    def _rewrite_line(
        self,
        *,
        line: str,
        current_division: str,
        active_record: str,
        replacement_engine: FieldReferenceReplacementEngine,
    ) -> str:
        if self.line_utils.is_comment_or_blank(line):
            return line

        if current_division != "PROCEDURE":
            return line

        if self.line_utils.has_existing_dclgen_reference(line):
            return line

        segments = self.line_utils.split_string_segments(line)
        rewritten_segments: list[str] = []

        for segment, is_string in segments:
            if is_string:
                rewritten_segments.append(segment)
                continue

            rewritten = replacement_engine.rewrite_qualified_references(segment)
            rewritten = replacement_engine.rewrite_bare_references(
                text=rewritten,
                active_record=active_record,
            )

            rewritten_segments.append(rewritten)

        return "".join(rewritten_segments)

    def _build_reference_maps(
        self,
    ) -> None:
        (
            self.record_field_map,
            self.record_group_map,
            self.table_record_map,
            self.group_record_map,
        ) = self.context_builder.build_reference_maps()


__all__ = [
    "FieldReferenceRewriter",
]