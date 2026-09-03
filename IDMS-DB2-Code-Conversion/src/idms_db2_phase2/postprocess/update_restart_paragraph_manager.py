from __future__ import annotations

from idms_db2_phase2.postprocess.cobol_update_standard_generator import (
    CobolUpdateStandardGenerator,
)
from idms_db2_phase2.postprocess.dynamic_metadata_resolver import UpdateProgramContext
from idms_db2_phase2.postprocess.update_postprocess_line_utils import (
    UpdatePostprocessLineUtils,
)
from rules.update_restart_rules import (
    RESTART_PARAGRAPH_NAMES,
    UPDATE_RESTART_DIAGNOSTICS,
    UPDATE_RESTART_WS_NAMES,
)


class UpdateRestartParagraphManager:
    def __init__(
        self,
        *,
        generator: CobolUpdateStandardGenerator,
        line_utils: UpdatePostprocessLineUtils,
    ) -> None:
        self.generator = generator
        self.line_utils = line_utils

    def ensure_read_flat_file(
        self,
        cobol_text: str,
        context: UpdateProgramContext,
        diagnostics: list[str],
    ) -> str:
        switch_group = UPDATE_RESTART_WS_NAMES["switch_group"]

        if not self.line_utils.logical_contains(
            cobol_text,
            f"01 {switch_group}.",
        ):
            diagnostics.append(
                "WS-SWITCHES not present. "
                "Skipped READ-FLAT-FILE enhancement."
            )
            return cobol_text

        paragraph = self.generator.read_flat_file(context)
        lines = self.line_utils.lines(cobol_text)

        existing_range = self.line_utils.find_paragraph_range(
            lines,
            "READ-FLAT-FILE",
        )

        if existing_range:
            start, end = existing_range
            updated_lines = lines[:start] + paragraph.splitlines() + [""] + lines[end:]
            diagnostics.append(UPDATE_RESTART_DIAGNOSTICS["read_replaced"])
            return self.line_utils.join(updated_lines)

        insert_index = self.line_utils.procedure_paragraph_insert_line_index(lines)

        if insert_index < 0:
            diagnostics.append(
                "Safe PROCEDURE DIVISION insertion point not found. "
                "Skipped READ-FLAT-FILE insertion."
            )
            return cobol_text

        updated_lines = (
            lines[:insert_index]
            + [""]
            + paragraph.splitlines()
            + [""]
            + lines[insert_index:]
        )
        diagnostics.append(UPDATE_RESTART_DIAGNOSTICS["read_added"])
        return self.line_utils.join(updated_lines)

    def ensure_restart_paragraphs(
        self,
        cobol_text: str,
        context: UpdateProgramContext,
        diagnostics: list[str],
    ) -> str:
        if not context.restart_dclgen:
            diagnostics.append(UPDATE_RESTART_DIAGNOSTICS["restart_missing"])
            return cobol_text

        switch_group = UPDATE_RESTART_WS_NAMES["switch_group"]
        help_group = UPDATE_RESTART_WS_NAMES["help_group"]

        if not self.line_utils.logical_contains(
            cobol_text,
            f"01 {switch_group}.",
        ) or not self.line_utils.logical_contains(
            cobol_text,
            f"01 {help_group}.",
        ):
            diagnostics.append(
                "Restart working-storage not present. "
                "Skipped restart paragraph injection."
            )
            return cobol_text

        restart_code = self.generator.restart_paragraphs(context)

        if not restart_code.strip():
            diagnostics.append("Restart generator produced no code. Skipped restart injection.")
            return cobol_text

        lines = self.line_utils.lines(cobol_text)

        updated_lines = self._remove_existing_restart_paragraphs(
            lines=lines,
        )

        insert_index = self.line_utils.procedure_paragraph_insert_line_index(
            updated_lines
        )

        if insert_index < 0:
            diagnostics.append(
                "Safe PROCEDURE DIVISION insertion point not found. "
                "Skipped restart paragraph injection."
            )
            return cobol_text

        final_lines = (
            updated_lines[:insert_index]
            + [""]
            + restart_code.splitlines()
            + [""]
            + updated_lines[insert_index:]
        )

        diagnostics.append(UPDATE_RESTART_DIAGNOSTICS["restart_inserted"])
        return self.line_utils.join(final_lines)

    def _remove_existing_restart_paragraphs(
        self,
        *,
        lines: list[str],
    ) -> list[str]:
        paragraph_names = [
            RESTART_PARAGRAPH_NAMES["control"],
            RESTART_PARAGRAPH_NAMES["restart_found"],
            RESTART_PARAGRAPH_NAMES["write_restart"],
            RESTART_PARAGRAPH_NAMES["commit"],
            RESTART_PARAGRAPH_NAMES["select"],
            RESTART_PARAGRAPH_NAMES["update"],
            RESTART_PARAGRAPH_NAMES["insert"],
            RESTART_PARAGRAPH_NAMES["abend"],
        ]

        updated = list(lines)

        for paragraph_name in paragraph_names:
            existing_range = self.line_utils.find_paragraph_range(
                updated,
                paragraph_name,
            )

            if not existing_range:
                continue

            start, end = existing_range
            updated = updated[:start] + updated[end:]

        return updated