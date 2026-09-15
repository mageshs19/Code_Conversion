# LOCATION: src/idms_db2_phase2/orchestration/conversion/conversion_pipeline.py
# ACTION: REPLACE ENTIRE FILE

from __future__ import annotations

from idms_db2_phase2.analyzers.program_flow_analyzer import ProgramFlowAnalyzer
from idms_db2_phase2.composers.counter_declaration_composer import (
    CounterDeclarationComposer,
)
from idms_db2_phase2.composers.late_db2_date_composer import (
    LateDb2DateComposer,
)
from idms_db2_phase2.composers.output_write_paragraph_composer import (
    OutputWriteParagraphComposer,
)
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
from idms_db2_phase2.validators.mapping_scope_filter import (
    MappingScopeFilter,
)
from idms_db2_phase2.validators.mapping_validator import MappingValidator


class ConversionPipeline:
    """Runs the linear IDMS->DB2 conversion pipeline.

    Depends on the host class for the component factory methods and message
    helpers (via mixins). Returns (converted_cobol, operations,
    dclgen_repository); validation messages are appended to the passed-in
    list.

    Pass-ordering contracts
    -----------------------
    0. ``MappingScopeFilter`` rescopes the mapping validation report to the
       program being converted. MappingValidator audits the WHOLE Sheet
       Mapping workbook, so a restart-table gap was reported as a blocking
       error against every retrieval program that never touches it. A gap
       stays an error for a table this program references, and becomes a
       workbook note for any other.

    1. ``feedback_cleanup`` (CobolCleanupComposer) runs
       ``OutputWritePlacementCleanup``, which lifts a guarded output WRITE
       out of the child-row paragraph into the PARENT paragraph, after the
       child cursor CLOSE. Left in the child-row paragraph the WRITE fires
       once per fetched child row instead of once per parent row.

    2. ``fixed_format`` sequences every line, including generator-inserted
       blocks.

    3. ``OutputWriteParagraphComposer`` extracts the record-population body
       into its own ``WRITE-<record>`` paragraph and replaces it with a
       PERFORM plus the output counter increment. It MUST run after both of
       the above:

         - before (1) it would extract from the wrong paragraph and bake in
           the once-per-child-row defect;
         - before (2) it would have no sequence area to clone when building
           the new paragraph header.

    4. ``LateDb2DateComposer`` re-runs the DB2 date and INITIALIZE passes.
       Those live inside ``feedback_cleanup`` and have already finished by
       the time step 3 moves the block into a brand new paragraph, so
       without this second run a DB2 date host field is moved straight into
       the output record, skipping the CCYYMMDD realignment. That is silent
       data corruption, not a formatting defect.

    5. ``CounterDeclarationComposer`` declares every ``WS-NB-*-COUNT`` the
       PROCEDURE DIVISION increments but WORKING-STORAGE does not define,
       and appends the end-of-run totals before STOP RUN. It MUST run after
       step 3, which is what emits the increment, and BEFORE step 7 so the
       generated DISPLAY lines are indented with everything else.

    6. ``UnmappedRecordBlockComposer`` comments record-level blocks that
       have no usable DB2 column mapping. Runs after the content passes so
       it never comments code another pass still needs to read.

    7. ``ProcedureIndentNormalizer`` re-anchors Area B, covering the
       paragraph created in step 3 and the totals added in step 5.

    8. ``FinalSequenceResequencerService`` rewrites columns 1-6 and 73-80,
       correcting the placeholder sequence numbers cloned in steps 3 and 5.
    """

    def _run_pipeline(
        self,
        *,
        conversion_input: ConversionInput,
        validation_messages: list[str],
    ) -> tuple[str, list, object]:
        repositories = self._repositories(conversion_input)
        resolvers = self._resolvers(repositories)
        generators = self._generators(
            repositories=repositories,
            resolvers=resolvers,
        )
        transformers = self._transformers(
            repositories=repositories,
            resolvers=resolvers,
            generators=generators,
        )
        composers = self._composers(
            repositories=repositories,
            resolvers=resolvers,
        )

        # ------------------------------------------------------------------
        # Input validation
        #
        # MappingValidator audits the ENTIRE Sheet Mapping workbook. A table
        # carrying rows but no usable DB2 columns is a genuine gap, but it
        # is a BLOCKER only for a program that references that table.
        # Reporting restart-table gaps against a read-only retrieval program
        # marked a clean conversion as Rejected, so the report is rescoped
        # here. Nothing is discarded: an out-of-scope gap is rewritten as a
        # workbook note rather than hidden.
        # ------------------------------------------------------------------
        mapping_validator = MappingValidator(
            mapping_repository=repositories["mapping"],
            dclgen_repository=repositories["dclgen"],
            table_name_resolver=resolvers["table_name"],
        )

        mapping_scope_filter = MappingScopeFilter(
            mapping_repository=repositories["mapping"],
            table_name_resolver=resolvers["table_name"],
        )
        validation_messages.extend(
            mapping_scope_filter.apply(
                messages=mapping_validator.validate(),
                source_text=conversion_input.idms_cobol_text,
            )
        )
        validation_messages.extend(
            self._component_messages(mapping_scope_filter)
        )

        # ------------------------------------------------------------------
        # IDMS -> DB2 statement transformation
        # ------------------------------------------------------------------
        converted_cobol, transform_messages, operations = transformers[
            "cobol"
        ].transform(
            cobol_text=conversion_input.idms_cobol_text,
            target_program_id=conversion_input.target_program_id,
        )
        validation_messages.extend(transform_messages)

        converted_cobol = composers["update_restart_skip"].compose(
            converted_cobol
        )
        validation_messages.extend(
            self._component_messages(composers["update_restart_skip"])
        )

        # ------------------------------------------------------------------
        # Program flow analysis (diagnostics only)
        # ------------------------------------------------------------------
        flow_analysis = ProgramFlowAnalyzer(
            mapping_rows=conversion_input.sheet_mapping_rows,
            dclgen_columns=conversion_input.dclgen_columns,
        ).analyze(
            cobol_text=conversion_input.idms_cobol_text,
            operations=operations,
        )
        validation_messages.extend(flow_analysis.diagnostics)

        # ------------------------------------------------------------------
        # Field references -> DCLGEN host variables
        # ------------------------------------------------------------------
        converted_cobol = transformers["field_reference"].rewrite(
            converted_cobol
        )
        validation_messages.extend(
            self._component_messages(transformers["field_reference"])
        )

        # ------------------------------------------------------------------
        # DB2 infrastructure, cursors
        # ------------------------------------------------------------------
        converted_cobol, infrastructure_messages = generators[
            "db2_infrastructure"
        ].apply(cobol_text=converted_cobol, operations=operations)
        validation_messages.extend(infrastructure_messages)

        converted_cobol = composers["cursor_order_cleanup"].compose(
            converted_cobol
        )

        converted_cobol, cursor_messages = generators[
            "cursor_paragraph"
        ].apply(cobol_text=converted_cobol, operations=operations)
        validation_messages.extend(cursor_messages)

        converted_cobol = composers["cursor_flow"].compose(converted_cobol)
        converted_cobol = composers["sqlcode_cleanup"].compose(converted_cobol)
        converted_cobol = composers["cursor_order_cleanup"].compose(
            converted_cobol
        )
        converted_cobol = composers["date_compare"].compose(converted_cobol)

        # ------------------------------------------------------------------
        # Timestamp / audit, SQLERROR routine
        # ------------------------------------------------------------------
        converted_cobol, timestamp_messages = generators["timestamp"].apply(
            cobol_text=converted_cobol,
            target_program_id=conversion_input.target_program_id,
        )
        validation_messages.extend(timestamp_messages)

        converted_cobol = generators["sql_error"].ensure_sql_error_paragraph(
            converted_cobol
        )

        # ------------------------------------------------------------------
        # Safe cleanup passes
        #
        # feedback_cleanup == CobolCleanupComposer. It runs
        # OutputWritePlacementCleanup, which moves the guarded output WRITE
        # out of the child-row paragraph into the parent paragraph. The
        # paragraph EXTRACTION below depends on that relocation having
        # already happened.
        # ------------------------------------------------------------------
        converted_cobol = composers["feedback_cleanup"].compose(
            converted_cobol
        )
        validation_messages.extend(
            self._component_messages(composers["feedback_cleanup"])
        )

        converted_cobol = composers["update_program_feedback"].compose(
            converted_cobol
        )
        validation_messages.extend(
            self._component_messages(composers["update_program_feedback"])
        )

        converted_cobol = composers["update_restart_skip"].compose(
            converted_cobol
        )
        validation_messages.extend(
            self._component_messages(composers["update_restart_skip"])
        )

        # ------------------------------------------------------------------
        # Layout
        # ------------------------------------------------------------------
        converted_cobol = composers["formatter"].format(converted_cobol)
        converted_cobol = composers["manual_layout"].compose(converted_cobol)
        converted_cobol = composers["style_preserver"].preserve(
            original_text=conversion_input.idms_cobol_text,
            converted_text=converted_cobol,
        )

        # Fixed-format ALL lines BEFORE commenting so generator-inserted
        # blocks are sequenced and comment lines cannot be collapsed (they do
        # not exist yet at this point).
        converted_cobol = composers["fixed_format"].format(converted_cobol)

        # ------------------------------------------------------------------
        # Output write paragraph extraction
        #
        # Lifts the record-population body out of the guard and into its own
        # WRITE-<record> paragraph, replacing it with a PERFORM plus the
        # output counter increment, matching the manual reference.
        #
        # Runs AFTER fixed_format so each generated line can clone a real
        # sequence area.
        # ------------------------------------------------------------------
        output_write_paragraph_composer = OutputWriteParagraphComposer()
        converted_cobol = output_write_paragraph_composer.compose(
            converted_cobol
        )
        validation_messages.extend(
            self._component_messages(output_write_paragraph_composer)
        )

        # ------------------------------------------------------------------
        # Late DB2 date conversion
        #
        # Db2DateOutputCleanup and InitializeBeforeOutputCleanup live inside
        # feedback_cleanup and have already finished. The write block only
        # just reached its final paragraph, so without this second run a DB2
        # date host field is moved straight into the output record and skips
        # the CCYYMMDD realignment. Idempotent: a converted move carries no
        # DCLGEN qualifier and cannot match again.
        # ------------------------------------------------------------------
        late_date_composer = LateDb2DateComposer()
        converted_cobol = late_date_composer.compose(converted_cobol)
        validation_messages.extend(
            self._component_messages(late_date_composer)
        )

        # ------------------------------------------------------------------
        # Counter declarations
        #
        # Declares every WS-NB-*-COUNT the PROCEDURE DIVISION increments but
        # WORKING-STORAGE does not define, and appends the end-of-run totals
        # before STOP RUN.
        #
        # Runs AFTER the extraction above, which is what emits the increment,
        # and BEFORE the indent normalizer so the generated DISPLAY lines are
        # aligned with every other statement.
        # ------------------------------------------------------------------
        counter_composer = CounterDeclarationComposer()
        converted_cobol = counter_composer.compose(converted_cobol)
        validation_messages.extend(
            self._component_messages(counter_composer)
        )

        # ------------------------------------------------------------------
        # LAST content pass: comment unmapped record blocks (record-level).
        # ------------------------------------------------------------------
        unmapped_block_composer = UnmappedRecordBlockComposer(
            table_name_resolver=resolvers["table_name"],
            column_name_resolver=resolvers["column_name"],
            original_idms_text=conversion_input.idms_cobol_text,
        )
        converted_cobol = unmapped_block_composer.compose(converted_cobol)
        validation_messages.extend(
            self._component_messages(unmapped_block_composer)
        )

        # Normalize PROCEDURE DIVISION Area-B indentation.
        # Covers the paragraph created by the extraction and the totals
        # added by the counter pass.
        indent_normalizer = ProcedureIndentNormalizer()
        converted_cobol = indent_normalizer.compose(converted_cobol)
        validation_messages.extend(
            self._component_messages(indent_normalizer)
        )

        # Re-sequence ONLY columns 1-6 and 73-80. Corrects the placeholder
        # sequence numbers cloned by the extraction and counter passes.
        converted_cobol = FinalSequenceResequencerService().resequence(
            converted_cobol
        )

        return converted_cobol, operations, repositories["dclgen"]