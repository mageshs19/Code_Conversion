# LOCATION: src/idms_db2_phase2/orchestration/conversion/conversion_pipeline.py
# ACTION: REPLACE ENTIRE FILE

from __future__ import annotations

from idms_db2_phase2.analyzers.program_flow_analyzer import ProgramFlowAnalyzer
from idms_db2_phase2.domain.models import ConversionInput
from idms_db2_phase2.orchestration.conversion.conversion_layout_pipeline import (
    ConversionLayoutPipeline,
)
from idms_db2_phase2.validators.mapping_scope_filter import (
    MappingScopeFilter,
)
from idms_db2_phase2.validators.mapping_validator import MappingValidator


class ConversionPipeline:
    """Runs the CONTENT phase of the IDMS->DB2 conversion.

    Depends on the host class for the component factory methods and message
    helpers (via mixins). Returns (converted_cobol, operations,
    dclgen_repository); validation messages are appended to the passed-in
    list.

    The FINISHING phase - layout, paragraph extraction, counters, indent and
    resequencing - lives in ConversionLayoutPipeline. That split keeps the
    two concerns testable in isolation: this class decides WHAT the program
    says, that class decides HOW it is laid out.

    Pass-ordering contracts (content phase)
    ---------------------------------------
    0a. ``LrfPathExpander`` rewrites Logical Record Facility syntax into the
        classic IDMS syntax the rest of the converter already understands::

            OBTAIN FIRST <LR> WHERE <keyword>  ->  OBTAIN FIRST <rec> WITHIN <set>
            LR-STATUS = 'X-EOA'                ->  DB-END-OF-SET
            FIELD OF <rec> OF LR               ->  FIELD OF <rec>

        It MUST run first, because MappingScopeFilter, CobolTransformer and
        ProgramFlowAnalyzer all read the source text. Every pass after this
        point sees classic IDMS and needs no logical-record knowledge.

    0b. ``MappingScopeFilter`` rescopes the mapping validation report to the
        program being converted. MappingValidator audits the WHOLE Sheet
        Mapping workbook, so a restart-table gap was reported as a blocking
        error against every retrieval program that never touches it. A gap
        stays an error for a table this program references, and becomes a
        workbook note for any other.

    1.  ``feedback_cleanup`` (CobolCleanupComposer) runs
        ``OutputWritePlacementCleanup``, which lifts a guarded output WRITE
        out of the child-row paragraph into the PARENT paragraph, after the
        child cursor CLOSE. Left in the child-row paragraph the WRITE fires
        once per fetched child row instead of once per parent row.

    Steps 2 through 8 are owned by ConversionLayoutPipeline and documented
    there.
    """

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
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
        # LRF -> classic IDMS expansion
        #
        # Must precede mapping scope, statement transformation and flow
        # analysis: all three read the program source. A program without
        # LRF metadata, or without LRF syntax, gets its text back unchanged.
        # ------------------------------------------------------------------
        source_text = self._expand_logical_records(
            conversion_input=conversion_input,
            transformers=transformers,
            validation_messages=validation_messages,
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
                source_text=source_text,
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
            cobol_text=source_text,
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
            cobol_text=source_text,
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
        converted_cobol = self._apply_db2_infrastructure(
            converted_cobol=converted_cobol,
            operations=operations,
            generators=generators,
            composers=composers,
            validation_messages=validation_messages,
        )

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
        # ------------------------------------------------------------------
        converted_cobol = self._apply_cleanup_composers(
            converted_cobol=converted_cobol,
            composers=composers,
            validation_messages=validation_messages,
        )

        # ------------------------------------------------------------------
        # FINISHING phase
        #
        # original_idms_text is the EXPANDED source, not the raw upload.
        # The converted text derives from it line by line, so style
        # preservation and unmapped-record discovery must compare against
        # the same baseline.
        # ------------------------------------------------------------------
        converted_cobol = ConversionLayoutPipeline(
            composers=composers,
            resolvers=resolvers,
            component_messages=self._component_messages,
        ).finish(
            converted_cobol=converted_cobol,
            original_idms_text=source_text,
            validation_messages=validation_messages,
        )

        return converted_cobol, operations, repositories["dclgen"]

    # ------------------------------------------------------------------
    # LRF expansion
    # ------------------------------------------------------------------
    def _expand_logical_records(
        self,
        *,
        conversion_input: ConversionInput,
        transformers: dict,
        validation_messages: list[str],
    ) -> str:
        """Rewrite LRF syntax into classic IDMS syntax.

        Returns the source text every later pass must use. Never raises:
        an expansion failure falls back to the original source and is
        reported as a validation message, because an unconverted LRF verb
        is caught downstream by the residual-IDMS checks anyway.
        """
        source_text = str(conversion_input.idms_cobol_text or "")

        expander = transformers.get("lrf_path_expander")
        if expander is None:
            return source_text

        try:
            expanded = expander.expand(source_text)
        except Exception as exc:  # noqa: BLE001
            validation_messages.append(
                "LRF expansion: skipped, original IDMS source will be used. "
                f"Reason: {exc}"
            )
            return source_text

        validation_messages.extend(self._component_messages(expander))

        return expanded or source_text

    # ------------------------------------------------------------------
    # DB2 infrastructure and cursor passes
    # ------------------------------------------------------------------
    #
    # DB2 infrastructure and cursor passes
    #
    #
    # DB2 infrastructure and cursor passes
    #
    def _apply_db2_infrastructure(
        self,
        *,
        converted_cobol: str,
        operations: list,
        generators: dict,
        composers: dict,
        validation_messages: list[str],
    ) -> str:
        
        converted_cobol, infrastructure_messages = generators[
            "db2_infrastructure"
        ].apply(cobol_text=converted_cobol, operations=operations)
        validation_messages.extend(infrastructure_messages)

        converted_cobol = composers["cursor_order_cleanup"].compose(
            converted_cobol
        )
        validation_messages.extend(
            self._component_messages(composers["cursor_order_cleanup"])
        )

        converted_cobol, cursor_messages = generators[
            "cursor_paragraph"
        ].apply(cobol_text=converted_cobol, operations=operations)
        validation_messages.extend(cursor_messages)

        #
        # Cursor driving flow.
        #
        converted_cobol = composers["cursor_flow"].compose(converted_cobol)
        validation_messages.extend(
            self._component_messages(composers["cursor_flow"])
        )

        #
        # Cursor close guarantee.
        #
        # Guarantees the three properties a generated cursor must hold,
        # whatever loop idiom the source used:
        #
        #   - the FETCH paragraph is driven UNTIL <cursor>-EOC,
        #   - the CLOSE paragraph is performed,
        #   - the fetched row reaches the business paragraph.
        #
        close_guarantee = composers.get("cursor_close_guarantee")

        if close_guarantee is None:
            validation_messages.append(
                "Cursor close guarantee: composer is not registered; a "
                "cursor whose driving loop could not be correlated will "
                "be opened without a loop, left unclosed, and its "
                "fetched row will not be processed."
            )
        else:
            converted_cobol = close_guarantee.compose(converted_cobol)
            validation_messages.extend(
                self._component_messages(close_guarantee)
            )

        converted_cobol = composers["sqlcode_cleanup"].compose(converted_cobol)
        validation_messages.extend(
            self._component_messages(composers["sqlcode_cleanup"])
        )

        converted_cobol = composers["cursor_order_cleanup"].compose(
            converted_cobol
        )
        validation_messages.extend(
            self._component_messages(composers["cursor_order_cleanup"])
        )

        #
        # DB2 DATE comparison realignment.
        #
        # A DB2 DATE host is DD.MM.CCYY, 10 bytes. A COBOL date field is
        # CCYYMMDD, PIC 9(8). Comparing them directly compares '0'
        # against '2' and selects the wrong rows, so this pass must be
        # visible in the log whether it fires or not.
        #
        date_compare = composers.get("date_compare")

        if date_compare is None:
            validation_messages.append(
                "DB2 date compare: composer is not registered; DATE host "
                "comparisons will not be realigned."
            )
        else:
            converted_cobol = date_compare.compose(converted_cobol)
            validation_messages.extend(
                self._component_messages(date_compare)
            )

        return converted_cobol
    # ------------------------------------------------------------------
    # Cleanup passes
    # ------------------------------------------------------------------
    def _apply_cleanup_composers(
        self,
        *,
        converted_cobol: str,
        composers: dict,
        validation_messages: list[str],
    ) -> str:
        """Content-level cleanup, before any layout decision is taken.

        feedback_cleanup == CobolCleanupComposer. It runs
        OutputWritePlacementCleanup, which moves the guarded output WRITE
        out of the child-row paragraph into the parent paragraph. The
        paragraph EXTRACTION in the finishing phase depends on that
        relocation having already happened.
        """
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

        return converted_cobol


__all__ = ["ConversionPipeline"]