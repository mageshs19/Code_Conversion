from __future__ import annotations

from idms_db2_phase2.postprocess.dynamic_metadata_resolver import UpdateProgramContext
from idms_db2_phase2.postprocess.main_flow.main_flow_line_utils import (
    MainFlowLineUtils,
)
from idms_db2_phase2.postprocess.main_flow.main_flow_locators import MainFlowLocators
from idms_db2_phase2.postprocess.main_flow.main_flow_paragraph_resolver import (
    MainFlowParagraphResolver,
)
from idms_db2_phase2.postprocess.update_postprocess_line_utils import (
    UpdatePostprocessLineUtils,
)
from rules.update_restart_rules import (
    MAIN_FLOW_CLOSE_LOOKBACK,
    MAIN_FLOW_DIAGNOSTICS,
    MAIN_FLOW_INITIALIZE_HELP_TEMPLATE,
    MAIN_FLOW_OPEN_LOOKBACK,
    MAIN_FLOW_PERFORM_READ_BODY,
    MAIN_FLOW_PERFORM_READ_BODY_DOT,
    MAIN_FLOW_RESTART_TEMPLATE_LINES,
    MAIN_FLOW_SET_NOT_EOF_TEMPLATE,
    RESTART_PARAGRAPH_NAMES,
    UPDATE_MAIN_DATE_INITIALIZATION_LINES,
    UPDATE_RESTART_DIAGNOSTICS,
    UPDATE_RESTART_WS_NAMES,
    UPDATE_SUMMARY_DISPLAY_TEMPLATES,
)


class UpdateMainFlowRewriter(
    MainFlowLineUtils,
    MainFlowParagraphResolver,
    MainFlowLocators,
):
    """Rewrites update-program main restart flow only.

    Update-postprocess only; does not touch retrieval. Orchestration and
    injection live here; line rendering, paragraph resolution, and locators
    are provided by mixins. All COBOL tokens, templates, and geometry live in
    rules/update_restart_rules.py.
    """

    def __init__(self, *, line_utils: UpdatePostprocessLineUtils) -> None:
        self.line_utils = line_utils

    def replace_legacy_restart_main_flow(
        self, cobol_text, context, diagnostics
    ):
        if not context.restart_dclgen:
            diagnostics.append(MAIN_FLOW_DIAGNOSTICS["dclgen_unresolved"])
            return cobol_text

        lines = self.line_utils.lines(cobol_text)
        open_index = self._find_open_input_index(
            lines=lines, file_name=context.input_file.name
        )
        if open_index < 0:
            diagnostics.append(MAIN_FLOW_DIAGNOSTICS["open_not_found"])
            return cobol_text

        stop_index = self._find_stop_run_index(lines=lines, start_index=open_index + 1)
        if stop_index < 0:
            diagnostics.append(MAIN_FLOW_DIAGNOSTICS["stop_not_found"])
            return cobol_text

        if not self._has_legacy_restart_between(
            lines=lines, start_index=open_index + 1, end_index=stop_index
        ):
            diagnostics.append(MAIN_FLOW_DIAGNOSTICS["legacy_not_found"])
            return cobol_text

        process_paragraph = self._resolve_process_paragraph_from_main_flow(
            lines=lines, start_index=open_index + 1, end_index=stop_index
        ) or self._resolve_first_business_paragraph(lines=lines)

        if not process_paragraph:
            diagnostics.append(MAIN_FLOW_DIAGNOSTICS["process_unresolved"])
            return cobol_text

        lines = self._ensure_main_initialization_before_open(
            lines=lines, open_index=open_index, context=context, diagnostics=diagnostics
        )

        open_index = self._find_open_input_index(
            lines=lines, file_name=context.input_file.name
        )
        stop_index = self._find_stop_run_index(lines=lines, start_index=open_index + 1)

        replacement = self._main_restart_flow_lines(
            context=context, process_paragraph=process_paragraph
        )
        updated_lines = lines[: open_index + 1] + replacement + lines[stop_index:]

        updated_lines = self._ensure_summary_display_before_close(
            lines=updated_lines, file_name=context.input_file.name, diagnostics=diagnostics
        )
        diagnostics.append(UPDATE_RESTART_DIAGNOSTICS["legacy_replaced"])

        updated_text = self.line_utils.join(updated_lines)
        return self.ensure_processing_paragraph_reads_next(
            cobol_text=updated_text,
            process_paragraph=process_paragraph,
            diagnostics=diagnostics,
        )

    def ensure_processing_paragraph_reads_next(
        self, *, cobol_text, process_paragraph, diagnostics
    ):
        if not process_paragraph:
            diagnostics.append(MAIN_FLOW_DIAGNOSTICS["process_empty"])
            return cobol_text

        lines = self.line_utils.lines(cobol_text)
        paragraph_range = self.line_utils.find_paragraph_range(lines, process_paragraph)
        if not paragraph_range:
            diagnostics.append(
                MAIN_FLOW_DIAGNOSTICS["process_not_found"].format(
                    paragraph=process_paragraph
                )
            )
            return cobol_text

        start, end = paragraph_range
        if self._paragraph_contains_perform_read_flat_file(lines[start:end]):
            diagnostics.append(
                MAIN_FLOW_DIAGNOSTICS["already_reads_next"].format(
                    paragraph=process_paragraph
                )
            )
            return cobol_text

        insert_index, use_existing_period = self._read_next_insert_plan(
            lines=lines, start=start, end=end
        )
        if insert_index < 0:
            diagnostics.append(
                MAIN_FLOW_DIAGNOSTICS["no_insertion_point"].format(
                    paragraph=process_paragraph
                )
            )
            return cobol_text

        body = (
            MAIN_FLOW_PERFORM_READ_BODY
            if use_existing_period
            else MAIN_FLOW_PERFORM_READ_BODY_DOT
        )
        reference_index = insert_index - 1 if insert_index > start else start
        read_line = self._line_like(reference_line=lines[reference_index], body=body)

        updated_lines = lines[:insert_index] + [read_line] + lines[insert_index:]
        diagnostics.append(
            MAIN_FLOW_DIAGNOSTICS["read_inserted"].format(paragraph=process_paragraph)
        )
        return self.line_utils.join(updated_lines)

    def _ensure_main_initialization_before_open(
        self, *, lines, open_index, context, diagnostics
    ):
        names = UPDATE_RESTART_WS_NAMES
        required_bodies = [
            MAIN_FLOW_SET_NOT_EOF_TEMPLATE.format(record=context.input_record_name),
            MAIN_FLOW_INITIALIZE_HELP_TEMPLATE.format(help_group=names["help_group"]),
            *UPDATE_MAIN_DATE_INITIALIZATION_LINES,
        ]

        existing_region = "\n".join(
            self._logical(line).upper()
            for line in lines[max(0, open_index - MAIN_FLOW_OPEN_LOOKBACK): open_index + 1]
        )
        missing_bodies = [
            body
            for body in required_bodies
            if body.upper().rstrip(".") not in existing_region.replace(".", "")
        ]
        if not missing_bodies:
            return lines

        reference_line = lines[open_index]
        new_lines = [
            self._line_like(reference_line=reference_line, body=body)
            for body in missing_bodies
        ]
        diagnostics.append(UPDATE_RESTART_DIAGNOSTICS["main_init_added"])
        return lines[:open_index] + new_lines + [""] + lines[open_index:]

    def _ensure_summary_display_before_close(
        self, *, lines, file_name, diagnostics
    ):
        names = UPDATE_RESTART_WS_NAMES
        close_index = self._find_close_input_index(lines=lines, file_name=file_name)
        if close_index < 0:
            return lines

        existing_region = "\n".join(
            self._logical(line).upper()
            for line in lines[max(0, close_index - MAIN_FLOW_CLOSE_LOOKBACK): close_index + 1]
        )
        display_bodies = [
            template.format(
                input_counter=names["input_counter"],
                update_counter=names["update_counter"],
            )
            for template in UPDATE_SUMMARY_DISPLAY_TEMPLATES
        ]
        missing_bodies = [
            body
            for body in display_bodies
            if body.upper().rstrip(".") not in existing_region.replace(".", "")
        ]
        if not missing_bodies:
            return lines

        reference_line = lines[close_index]
        new_lines = [
            self._line_like(reference_line=reference_line, body=body)
            for body in missing_bodies
        ]
        diagnostics.append(UPDATE_RESTART_DIAGNOSTICS["summary_display_added"])
        return lines[:close_index] + new_lines + lines[close_index:]

    def _main_restart_flow_lines(self, *, context, process_paragraph):
        return [
            template.format(
                control=RESTART_PARAGRAPH_NAMES["control"],
                commit=RESTART_PARAGRAPH_NAMES["commit"],
                process_paragraph=process_paragraph,
                record=context.input_record_name,
                file_name=context.input_file.name,
            )
            for template in MAIN_FLOW_RESTART_TEMPLATE_LINES
        ]