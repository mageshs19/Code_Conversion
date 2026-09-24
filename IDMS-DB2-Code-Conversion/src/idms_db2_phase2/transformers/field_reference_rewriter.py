# LOCATION: src/idms_db2_phase2/transformers/field_reference_rewriter.py
# ACTION: REPLACE ENTIRE FILE

from __future__ import annotations

from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
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
from rules.field_reference_rewriter_rules import (
    ALLOW_REWRITE_WRAPPING,
    ENFORCE_FIXED_FORMAT_REWRITE,
    FIELD_REFERENCE_GEOMETRY_MESSAGES,
)

PROCEDURE_DIVISION_NAME = "PROCEDURE"
BLANK_INDICATOR = " "
LINE_ENDINGS = "\r\n"


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

    CORRECTION 1 - the rewrite broke fixed-format geometry
    -------------------------------------------------------
    _rewrite_line substituted into the WHOLE record, sequence areas
    included. A qualified rewrite is almost always longer than what it
    replaces:

        DA-CPTA-FORM-AS OF VMBFAS         25 characters
        DA-CPTAFS-479BFAS OF DCLDZBFASTV  32 characters

    so an 80-column record became 87 and the right sequence 00002020
    moved from column 73 to column 80. Later passes read the first
    displaced digit as body text and emitted

        AND HELP-DA-CPTAFS-479BFAS NOT = '00000000') OR 0

    Substitution now happens inside columns 8-72 ONLY, and the record is
    reassembled from its own left sequence, indicator and right sequence.

    CORRECTION 2 - trailing blanks were stripped
    ---------------------------------------------
    `line = raw_line.rstrip()` removed the body padding that positions
    the right sequence at column 73. Only the line ending is stripped
    now; columns 8-72 keep their blanks.

    CORRECTION 3 - an over-long rewrite had nowhere to go
    ------------------------------------------------------
    A body that no longer fits 65 columns is WRAPPED at word boundaries
    onto further physical lines. _rewrite_line therefore returns a LIST,
    and the caller extends rather than appends. When even a wrapped form
    cannot be represented the original line is kept and reported: a
    rewrite that cannot be rendered must never corrupt the record.

    CORRECTION 4 - reference-map building was a tail method
    --------------------------------------------------------
    _build_reference_maps was the last method before __all__ and was
    lost in transit, producing

        AttributeError: 'FieldReferenceRewriter' object has no
        attribute '_build_reference_maps'

    rewrite() now calls the context builder directly, so no helper is
    required, and the helper itself is declared next to __init__.
    """

    def __init__(
        self,
        mapping_repository: MappingRepository,
        table_name_resolver: TableNameResolver,
        host_variable_resolver: HostVariableResolver,
        fixed_format: FixedFormatLineService | None = None,
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
        self.fixed_format = fixed_format or FixedFormatLineService()
        self.context_builder = FieldReferenceContextBuilder(
            mapping_repository=mapping_repository,
            table_name_resolver=table_name_resolver,
            host_variable_resolver=host_variable_resolver,
        )

    def _build_reference_maps(self) -> None:
        """Retained for any external caller. rewrite() does not need it."""
        (
            self.record_field_map,
            self.record_group_map,
            self.table_record_map,
            self.group_record_map,
        ) = self.context_builder.build_reference_maps()

    #
    # Public entry point
    #
    def rewrite(
        self,
        text: str,
    ) -> str:
        self.rewrite_messages = []
        self.messages = self.rewrite_messages

        if not text:
            return ""

        # Inlined deliberately: a helper declared at the tail of the class
        # has already gone missing once.
        (
            self.record_field_map,
            self.record_group_map,
            self.table_record_map,
            self.group_record_map,
        ) = self.context_builder.build_reference_maps()

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

        current_division = (
            PROCEDURE_DIVISION_NAME if not has_any_division else ""
        )
        active_record = ""

        for raw_line in lines:
            # Only the line ending is removed. Trailing blanks are part
            # of a fixed-format record: they position the right sequence
            # at column 73.
            line = raw_line.rstrip(LINE_ENDINGS)
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

            output_lines.extend(
                self._rewrite_line(
                    line=line,
                    current_division=current_division,
                    active_record=active_record,
                    replacement_engine=replacement_engine,
                )
            )

        return "\n".join(output_lines).rstrip() + "\n"

    #
    # One line
    #
    def _rewrite_line(
        self,
        *,
        line: str,
        current_division: str,
        active_record: str,
        replacement_engine: FieldReferenceReplacementEngine,
    ) -> list[str]:
        """Rewrite one line. Returns one line, or several when wrapped."""
        if self.line_utils.is_comment_or_blank(line):
            return [line]

        if current_division != PROCEDURE_DIVISION_NAME:
            return [line]

        if self.line_utils.has_existing_dclgen_reference(line):
            return [line]

        if not ENFORCE_FIXED_FORMAT_REWRITE or not self._is_fixed(line):
            return [
                self._rewrite_text(
                    text=line,
                    active_record=active_record,
                    replacement_engine=replacement_engine,
                )
            ]

        left, indicator, body, right = self._split(line)

        new_body = self._rewrite_text(
            text=body,
            active_record=active_record,
            replacement_engine=replacement_engine,
        )

        if new_body == body:
            return [line]

        rebuilt = self._build(left, indicator, new_body, right)

        if rebuilt is not None:
            return [rebuilt]

        if ALLOW_REWRITE_WRAPPING:
            wrapped = self._wrap(line, new_body)

            if wrapped:
                self.rewrite_messages.append(
                    FIELD_REFERENCE_GEOMETRY_MESSAGES["wrapped"].format(
                        count=len(wrapped),
                    )
                )
                return list(wrapped)

        self.rewrite_messages.append(
            FIELD_REFERENCE_GEOMETRY_MESSAGES["refused"].format(
                body=new_body.strip(),
            )
        )

        return [line]

    def _rewrite_text(
        self,
        *,
        text: str,
        active_record: str,
        replacement_engine: FieldReferenceReplacementEngine,
    ) -> str:
        """Apply both rewrites to one span, string literals protected."""
        segments = self.line_utils.split_string_segments(text)
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

    #
    # Fixed-format access, all total functions
    #
    def _is_fixed(self, line: str) -> bool:
        try:
            return bool(self.fixed_format.is_fixed_line(line))
        except Exception:  # noqa: BLE001
            return False

    def _split(self, line: str) -> tuple[str, str, str, str]:
        try:
            left, indicator, body, right = self.fixed_format.split(line)
            return (
                str(left or ""),
                str(indicator or BLANK_INDICATOR),
                str(body or ""),
                str(right or ""),
            )
        except Exception:  # noqa: BLE001
            return "", BLANK_INDICATOR, str(line or ""), ""

    def _build(
        self,
        left: str,
        indicator: str,
        body: str,
        right: str,
    ) -> str | None:
        try:
            return self.fixed_format.build_or_none(
                left,
                indicator or BLANK_INDICATOR,
                body,
                right,
            )
        except Exception:  # noqa: BLE001
            return None

    def _wrap(self, line: str, body: str) -> list[str]:
        try:
            return list(
                self.fixed_format.replace_body_wrapped(line, body) or []
            )
        except Exception:  # noqa: BLE001
            return []


__all__ = [
    "FieldReferenceRewriter",
]