from __future__ import annotations

from idms_db2_phase2.analyzers.program_flow_analyzer import ProgramFlowAnalyzer
from idms_db2_phase2.composers.procedure_indent_normalizer import (
    ProcedureIndentNormalizer,
)
from idms_db2_phase2.composers.unmapped_record_block_composer import (
    UnmappedRecordBlockComposer,
)
from idms_db2_phase2.domain.models import ConversionInput
from idms_db2_phase2.services.final_sequence_resequencer_service import (
    FinalSequenceResequencerService,
)
from idms_db2_phase2.validators.mapping_validator import MappingValidator


class ConversionPipeline:
    """Runs the linear IDMS->DB2 conversion pipeline.

    Depends on the host class for the component factory methods and message
    helpers (via mixins). Returns (converted_cobol, operations); validation
    messages are appended to the passed-in list.
    """

    def _run_pipeline(
        self,
        *,
        conversion_input: ConversionInput,
        validation_messages: list[str],
    ) -> tuple[str, list]:
        repositories = self._repositories(conversion_input)
        resolvers = self._resolvers(repositories)
        generators = self._generators(repositories=repositories, resolvers=resolvers)
        transformers = self._transformers(
            repositories=repositories,
            resolvers=resolvers,
            generators=generators,
        )
        composers = self._composers(repositories=repositories, resolvers=resolvers)

        mapping_validator = MappingValidator(
            mapping_repository=repositories["mapping"],
            dclgen_repository=repositories["dclgen"],
            table_name_resolver=resolvers["table_name"],
        )
        validation_messages.extend(mapping_validator.validate())

        converted_cobol, transform_messages, operations = transformers[
            "cobol"
        ].transform(
            cobol_text=conversion_input.idms_cobol_text,
            target_program_id=conversion_input.target_program_id,
        )
        validation_messages.extend(transform_messages)

        converted_cobol = composers["update_restart_skip"].compose(converted_cobol)
        validation_messages.extend(
            self._component_messages(composers["update_restart_skip"])
        )

        flow_analysis = ProgramFlowAnalyzer(
            mapping_rows=conversion_input.sheet_mapping_rows,
            dclgen_columns=conversion_input.dclgen_columns,
        ).analyze(
            cobol_text=conversion_input.idms_cobol_text,
            operations=operations,
        )
        validation_messages.extend(flow_analysis.diagnostics)

        converted_cobol = transformers["field_reference"].rewrite(converted_cobol)
        validation_messages.extend(
            self._component_messages(transformers["field_reference"])
        )

        converted_cobol, infrastructure_messages = generators[
            "db2_infrastructure"
        ].apply(cobol_text=converted_cobol, operations=operations)
        validation_messages.extend(infrastructure_messages)

        converted_cobol = composers["cursor_order_cleanup"].compose(converted_cobol)

        converted_cobol, cursor_messages = generators["cursor_paragraph"].apply(
            cobol_text=converted_cobol, operations=operations
        )
        validation_messages.extend(cursor_messages)

        converted_cobol = composers["cursor_flow"].compose(converted_cobol)
        converted_cobol = composers["sqlcode_cleanup"].compose(converted_cobol)
        converted_cobol = composers["cursor_order_cleanup"].compose(converted_cobol)
        converted_cobol = composers["date_compare"].compose(converted_cobol)

        converted_cobol, timestamp_messages = generators["timestamp"].apply(
            cobol_text=converted_cobol,
            target_program_id=conversion_input.target_program_id,
        )
        validation_messages.extend(timestamp_messages)

        converted_cobol = generators["sql_error"].ensure_sql_error_paragraph(
            converted_cobol
        )

        converted_cobol = composers["feedback_cleanup"].compose(converted_cobol)
        validation_messages.extend(
            self._component_messages(composers["feedback_cleanup"])
        )

        converted_cobol = composers["update_program_feedback"].compose(
            converted_cobol
        )
        validation_messages.extend(
            self._component_messages(composers["update_program_feedback"])
        )

        converted_cobol = composers["update_restart_skip"].compose(converted_cobol)
        validation_messages.extend(
            self._component_messages(composers["update_restart_skip"])
        )

        converted_cobol = composers["formatter"].format(converted_cobol)
        converted_cobol = composers["manual_layout"].compose(converted_cobol)
        converted_cobol = composers["style_preserver"].preserve(
            original_text=conversion_input.idms_cobol_text,
            converted_text=converted_cobol,
        )

        # Fixed-format ALL lines BEFORE commenting so generator-inserted blocks
        # are sequenced and comment lines cannot be collapsed (they do not
        # exist yet at this point).
        converted_cobol = composers["fixed_format"].format(converted_cobol)

        # LAST content pass: comment unmapped record blocks (record-level).
        unmapped_block_composer = UnmappedRecordBlockComposer(
            table_name_resolver=resolvers["table_name"],
            column_name_resolver=resolvers["column_name"],
            original_idms_text=conversion_input.idms_cobol_text,
        )
        converted_cobol = unmapped_block_composer.compose(converted_cobol)
        validation_messages.extend(
            self._component_messages(unmapped_block_composer)
        )

        # Normalize PROCEDURE DIVISION Area-B indentation to 4 spaces.
        indent_normalizer = ProcedureIndentNormalizer()
        converted_cobol = indent_normalizer.compose(converted_cobol)
        validation_messages.extend(
            self._component_messages(indent_normalizer)
        )

        # Re-sequence ONLY columns 1-6 and 73-80.
        converted_cobol = FinalSequenceResequencerService().resequence(
            converted_cobol
        )

        return converted_cobol, operations, repositories["dclgen"]