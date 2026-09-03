from __future__ import annotations

from idms_db2_phase2.postprocess.dynamic_metadata_resolver import (
    DclgenRoleInfo,
    UpdateProgramContext,
)
from rules.update_restart_rules import (
    RESTART_DEFAULT_PHASE,
    RESTART_INSERT_QUERYNO,
    RESTART_PARAGRAPH_NAMES,
    RESTART_RETENTION_DAYS,
    RESTART_SELECT_QUERYNO,
    RESTART_STATUS_COMPLETE,
    RESTART_STATUS_INCOMPLETE,
    RESTART_UPDATE_QUERYNO,
    UPDATE_RESTART_WS_NAMES,
    UPDATE_STANDARD_DATE_WS_LINES,
)
from rules.update_standard_generator_templates import (
    ABEND_CALL_STATEMENT,
    COMMIT_COUNTER_LEGACY,
    COMMIT_COUNTER_RESET_VALUE,
    COPYBOOK_INCLUDE_TEMPLATE,
    CS_PROGRAM_FIELD,
    DA_DD_MM_CCYY_FIELD,
    DCLGEN_INCLUDE_TEMPLATE,
    DISPLAY_ERROR_REC_TEMPLATE,
    DISPLAY_PREVIOUS_RUN_COMPLETE,
    EOF_NOT_SET_VALUE,
    EOF_SET_VALUE,
    PROCESS_COMMIT_TEMPLATE,
    READ_FLAT_FILE_TEMPLATE,
    RESTART_CONTROL_TEMPLATE,
    RESTART_FOUND_TEMPLATE,
    RESTART_LENGTH_BASE,
    RESTART_SQL_TEMPLATE,
    SQL_ERROR_PARAGRAPH,
    WORKING_STORAGE_TEMPLATE,
    WRITE_RESTART_TEMPLATE,
)


class CobolUpdateStandardGenerator:
    """Generates update-program COBOL snippets from resolved metadata.

    The generator owns no COBOL layout literals: every template lives in
    rules/update_standard_generator_templates.py. Only dynamic metadata
    (record, field, table, host names) is substituted here. No source
    program, copybook, DB2 table, DCLGEN, or host variable name is hardcoded.
    """

    def copybook_include(self, context: UpdateProgramContext) -> str:
        return COPYBOOK_INCLUDE_TEMPLATE.format(
            include=context.copybook_include_name
        )

    def dclgen_include(self, role: DclgenRoleInfo) -> str:
        return DCLGEN_INCLUDE_TEMPLATE.format(include=role.include_name)

    def dclgen_include_by_name(self, include_name: str) -> str:
        return DCLGEN_INCLUDE_TEMPLATE.format(
            include=str(include_name or "").strip().upper()
        )

    def working_storage(self, context: UpdateProgramContext) -> str:
        names = UPDATE_RESTART_WS_NAMES
        length = context.record_length
        return WORKING_STORAGE_TEMPLATE.format(
            switch_group=names["switch_group"],
            record=context.input_record_name,
            eof_not=EOF_NOT_SET_VALUE,
            eof_set=EOF_SET_VALUE,
            help_group=names["help_group"],
            restart_record=names["restart_record"],
            read_count=names["read_count"],
            restart_key=names["restart_key"],
            input_save_area=names["input_save_area"],
            commit_counter=names["commit_counter"],
            input_counter=names["input_counter"],
            update_counter=names["update_counter"],
            restart_len=names["restart_len"],
            length=length,
            restart_length=RESTART_LENGTH_BASE + length,
        )

    def date_working_storage(self) -> str:
        return "\n".join(UPDATE_STANDARD_DATE_WS_LINES)

    def read_flat_file(self, context: UpdateProgramContext) -> str:
        names = UPDATE_RESTART_WS_NAMES
        return READ_FLAT_FILE_TEMPLATE.format(
            record=context.input_record_name,
            file_name=context.input_file.name,
            commit_counter=names["commit_counter"],
            input_counter=names["input_counter"],
            input_save_area=names["input_save_area"],
        )

    def restart_paragraphs(self, context: UpdateProgramContext) -> str:
        parts = [
            self.restart_control(context),
            self.restart_found(context),
            self.write_restart(context),
            self.process_commit(context),
            self.restart_sql(context),
        ]
        return "\n\n".join(part for part in parts if part.strip())

    def restart_control(self, context: UpdateProgramContext) -> str:
        role = context.restart_dclgen
        if not role:
            return ""

        p = RESTART_PARAGRAPH_NAMES
        return RESTART_CONTROL_TEMPLATE.format(
            control=p["control"],
            cs_program=CS_PROGRAM_FIELD,
            da_field=DA_DD_MM_CCYY_FIELD,
            program_field=role.program_field,
            date_field=role.date_field,
            phase_field=role.phase_field,
            host_record=role.host_record_name,
            default_phase=RESTART_DEFAULT_PHASE,
            select=p["select"],
            restart_found=p["restart_found"],
            write_restart=p["write_restart"],
            sql_error=SQL_ERROR_PARAGRAPH,
            commit_reset=COMMIT_COUNTER_RESET_VALUE,
            commit_counter_legacy=COMMIT_COUNTER_LEGACY,
        )

    def restart_found(self, context: UpdateProgramContext) -> str:
        role = context.restart_dclgen
        if not role:
            return ""

        p = RESTART_PARAGRAPH_NAMES
        names = UPDATE_RESTART_WS_NAMES
        return RESTART_FOUND_TEMPLATE.format(
            restart_found=p["restart_found"],
            payload_text_field=role.payload_text_field,
            host_record=role.host_record_name,
            restart_record=names["restart_record"],
            status_field=role.status_field,
            status_complete=RESTART_STATUS_COMPLETE,
            display_complete=DISPLAY_PREVIOUS_RUN_COMPLETE,
            abend=p["abend"],
            read_count=names["read_count"],
            input_counter=names["input_counter"],
        )

    def write_restart(self, context: UpdateProgramContext) -> str:
        role = context.restart_dclgen
        if not role:
            return ""

        p = RESTART_PARAGRAPH_NAMES
        names = UPDATE_RESTART_WS_NAMES
        return WRITE_RESTART_TEMPLATE.format(
            write_restart=p["write_restart"],
            status_incomplete=RESTART_STATUS_INCOMPLETE,
            status_field=role.status_field,
            host_record=role.host_record_name,
            retention_days=RESTART_RETENTION_DAYS,
            retention_field=role.retention_field,
            restart_len=names["restart_len"],
            payload_len_field=role.payload_len_field,
            input_counter=names["input_counter"],
            read_count=names["read_count"],
            restart_record=names["restart_record"],
            restart_key=names["restart_key"],
            payload_text_field=role.payload_text_field,
            insert=p["insert"],
        )

    def process_commit(self, context: UpdateProgramContext) -> str:
        role = context.restart_dclgen
        if not role:
            return ""

        p = RESTART_PARAGRAPH_NAMES
        names = UPDATE_RESTART_WS_NAMES
        return PROCESS_COMMIT_TEMPLATE.format(
            commit=p["commit"],
            commit_counter=names["commit_counter"],
            input_counter=names["input_counter"],
            read_count=names["read_count"],
            restart_record=names["restart_record"],
            input_save_area=names["input_save_area"],
            restart_key=names["restart_key"],
            record=context.input_record_name,
            status_complete=RESTART_STATUS_COMPLETE,
            status_incomplete=RESTART_STATUS_INCOMPLETE,
            status_field=role.status_field,
            host_record=role.host_record_name,
            restart_len=names["restart_len"],
            payload_len_field=role.payload_len_field,
            payload_text_field=role.payload_text_field,
            update=p["update"],
            display_error=DISPLAY_ERROR_REC_TEMPLATE.format(
                counter=names["input_counter"]
            ),
            sql_error=SQL_ERROR_PARAGRAPH,
        )

    def restart_sql(self, context: UpdateProgramContext) -> str:
        role = context.restart_dclgen
        if not role:
            return ""

        p = RESTART_PARAGRAPH_NAMES
        names = UPDATE_RESTART_WS_NAMES
        display_error = DISPLAY_ERROR_REC_TEMPLATE.format(
            counter=names["input_counter"]
        )
        return RESTART_SQL_TEMPLATE.format(
            select=p["select"],
            update=p["update"],
            insert=p["insert"],
            abend=p["abend"],
            program_column=role.program_column,
            phase_column=role.phase_column,
            date_column=role.date_column,
            status_column=role.status_column,
            retention_column=role.retention_column,
            payload_column=role.payload_column,
            host_record=role.host_record_name,
            program_field=role.program_field,
            phase_field=role.phase_field,
            date_field=role.date_field,
            status_field=role.status_field,
            retention_field=role.retention_field,
            payload_group=role.payload_group,
            table_name=role.table_name,
            select_queryno=RESTART_SELECT_QUERYNO,
            update_queryno=RESTART_UPDATE_QUERYNO,
            insert_queryno=RESTART_INSERT_QUERYNO,
            display_error=display_error,
            sql_error=SQL_ERROR_PARAGRAPH,
            abend_call=ABEND_CALL_STATEMENT,
        )