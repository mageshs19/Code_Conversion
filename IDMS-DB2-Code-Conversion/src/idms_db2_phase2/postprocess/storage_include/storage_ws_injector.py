from __future__ import annotations

from idms_db2_phase2.postprocess.dynamic_metadata_resolver import UpdateProgramContext
from patterns.update_restart_patterns import (
    MALFORMED_SQLERROR_END_EVALUATE_PATTERN,
)
from patterns.update_storage_include_patterns import (
    CS_PROGRAM_01_PATTERN,
    PROGRAM_NAME_MOVE_PATTERN,
)
from rules.update_restart_rules import (
    UPDATE_RESTART_DIAGNOSTICS,
    UPDATE_RESTART_WS_NAMES,
)
from rules.update_storage_include_rules import (
    CS_PROGRAM_77_TEMPLATE,
    DATE_WS_ANCHORS,
    PROGRAM_NAME_MOVE_REPLACEMENT_TEMPLATE,
    SKIP_DATA_DIVISION_DATE_WS,
    SKIP_DATA_DIVISION_WS,
    WS_ANCHOR_01_TEMPLATE,
)


class StorageWsInjector:
    """Working-storage, date-WS, program-name and SQLERROR passes.

    Depends on the host class for ``self.line_utils`` and ``self.generator``.
    """

    def fix_malformed_sqlerror(self, cobol_text, diagnostics):
        updated = MALFORMED_SQLERROR_END_EVALUATE_PATTERN.sub(
            "PERFORM SQLERROR\nEND-EVALUATE",
            cobol_text,
        )
        if updated != cobol_text:
            diagnostics.append(UPDATE_RESTART_DIAGNOSTICS["malformed_sqlerror_fixed"])
        return updated

    def normalize_program_name(self, cobol_text, context, diagnostics):
        program_id = str(context.program_id or "").strip().upper()
        if not program_id:
            return cobol_text

        updated = PROGRAM_NAME_MOVE_PATTERN.sub(
            PROGRAM_NAME_MOVE_REPLACEMENT_TEMPLATE.format(program_id=program_id),
            cobol_text,
        )
        updated = CS_PROGRAM_01_PATTERN.sub(
            lambda match: CS_PROGRAM_77_TEMPLATE.format(
                prefix=match.group("prefix"),
                program_id=program_id,
            ),
            updated,
        )
        if updated != cobol_text:
            diagnostics.append(UPDATE_RESTART_DIAGNOSTICS["program_name_normalized"])
        return updated

    def ensure_working_storage(self, cobol_text, context, diagnostics):
        names = UPDATE_RESTART_WS_NAMES
        switch_anchor = WS_ANCHOR_01_TEMPLATE.format(group=names["switch_group"])
        help_anchor = WS_ANCHOR_01_TEMPLATE.format(group=names["help_group"])

        if self.line_utils.logical_contains(
            cobol_text, switch_anchor
        ) and self.line_utils.logical_contains(cobol_text, help_anchor):
            diagnostics.append(UPDATE_RESTART_DIAGNOSTICS["ws_exists"])
            return cobol_text

        lines = self.line_utils.lines(cobol_text)
        insert_index = self.line_utils.data_division_insert_line_index(lines)
        if insert_index < 0:
            diagnostics.append(SKIP_DATA_DIVISION_WS)
            return cobol_text

        block = self.generator.working_storage(context).splitlines()
        updated_lines = lines[:insert_index] + block + [""] + lines[insert_index:]
        diagnostics.append(UPDATE_RESTART_DIAGNOSTICS["ws_injected"])
        return self.line_utils.join(updated_lines)

    def ensure_date_working_storage(self, cobol_text, diagnostics):
        if any(
            self.line_utils.logical_contains(cobol_text, anchor)
            for anchor in DATE_WS_ANCHORS
        ):
            diagnostics.append(UPDATE_RESTART_DIAGNOSTICS["date_ws_exists"])
            return cobol_text

        lines = self.line_utils.lines(cobol_text)
        insert_index = self.line_utils.data_division_insert_line_index(lines)
        if insert_index < 0:
            diagnostics.append(SKIP_DATA_DIVISION_DATE_WS)
            return cobol_text

        block = self.generator.date_working_storage().splitlines()
        updated_lines = lines[:insert_index] + block + [""] + lines[insert_index:]
        diagnostics.append(UPDATE_RESTART_DIAGNOSTICS["date_ws_injected"])
        return self.line_utils.join(updated_lines)