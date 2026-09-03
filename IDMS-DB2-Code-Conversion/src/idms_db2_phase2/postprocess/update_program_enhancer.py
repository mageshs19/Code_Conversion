from __future__ import annotations

from idms_db2_phase2.postprocess.cobol_update_standard_generator import (
    CobolUpdateStandardGenerator,
)
from idms_db2_phase2.postprocess.dynamic_metadata_resolver import (
    DynamicMetadataResolver,
)
from idms_db2_phase2.postprocess.update_business_sql_standardizer import (
    UpdateBusinessSqlStandardizer,
)
from idms_db2_phase2.postprocess.update_enhancement_result import (
    EnhancementResult,
)
from idms_db2_phase2.postprocess.update_main_flow_rewriter import (
    UpdateMainFlowRewriter,
)
from idms_db2_phase2.postprocess.update_postprocess_line_utils import (
    UpdatePostprocessLineUtils,
)
from idms_db2_phase2.postprocess.update_restart_paragraph_manager import (
    UpdateRestartParagraphManager,
)
from idms_db2_phase2.postprocess.update_storage_include_manager import (
    UpdateStorageIncludeManager,
)
from rules.update_restart_rules import UPDATE_RESTART_DIAGNOSTICS
from idms_db2_phase2.repositories.mapping_repository import MappingRepository   # ADDED


class UpdateProgramEnhancer:
    """
    Update-program-only postprocess enhancer.

    This class is deliberately not used by retrieval.
    It uses metadata already parsed by the normal application flow and applies
    only update restart/input handling fixes.
    """

    def __init__(self) -> None:
        self.resolver = DynamicMetadataResolver()
        self.generator = CobolUpdateStandardGenerator()
        self.line_utils = UpdatePostprocessLineUtils()

        self.storage_include_manager = UpdateStorageIncludeManager(
            generator=self.generator,
            line_utils=self.line_utils,
        )

        self.main_flow_rewriter = UpdateMainFlowRewriter(
            line_utils=self.line_utils,
        )

        self.restart_paragraph_manager = UpdateRestartParagraphManager(
            generator=self.generator,
            line_utils=self.line_utils,
        )

        self.business_sql_standardizer = UpdateBusinessSqlStandardizer(
            line_utils=self.line_utils,
        )

    def enhance(
        self,
        *,
        source_cobol: str,
        converted_cobol: str,
        copybook_fields: list,
        dclgen_columns: list,
        target_program_id: str = "",
        sheet_mapping_rows: list | None = None,   # ADDED: Sheet Mapping authority
    ) -> EnhancementResult:
        diagnostics: list[str] = [UPDATE_RESTART_DIAGNOSTICS["start"]]

        # ADDED: Sheet Mapping authority for the restart AND-gate.
        # Sheet Mapping is the authority for DB2 table names (authority_rules).
        # It is required to prevent DCLGEN-only fabrication of restart SQL
        # (Case 3). Defaults to an empty repository when rows are not supplied,
        # which keeps the AND-gate closed (safe skip) rather than fabricating.
        mapping_repository = MappingRepository(sheet_mapping_rows or [])

        try:
            context = self.resolver.resolve(
                source_cobol=source_cobol,
                generated_cobol=converted_cobol,
                copybook_fields=copybook_fields,
                dclgen_columns=dclgen_columns,
                target_program_id=target_program_id,
                mapping_repository=mapping_repository,   # ADDED
            )
        except Exception as exc:
            diagnostics.append(
                f"{UPDATE_RESTART_DIAGNOSTICS['context_failed']} Reason: {exc}"
            )
            diagnostics.append(UPDATE_RESTART_DIAGNOSTICS["end"])

            return EnhancementResult(
                converted_cobol=converted_cobol,
                diagnostics=diagnostics,
            )

        diagnostics.extend(context.diagnostics)

        # --- Split Case 2 vs Case 3 warnings -----------------------------
        # When restart_dclgen is None, no restart SQL is generated and the
        # legacy IDMS restart/control flow is preserved unchanged. We split
        # the diagnostic so operators can tell WHY it was skipped:
        #   Case 3: DCLGEN restart group existed but Sheet Mapping did not
        #           confirm the restart table (AND-gate blocked fabrication).
        #   Case 2/4: restart DCLGEN itself was not resolved.
        if getattr(context, "restart_dclgen", None) is None:
            has_dclgen_restart_candidate = bool(dclgen_columns)
            mapping_has_restart_hint = any(
                mapping_repository.has_table(t)
                for t in mapping_repository.tables()
            )

            if has_dclgen_restart_candidate and mapping_has_restart_hint:
                # Case 3: DCLGEN present, but mapping did not confirm the table.
                diagnostics.append(
                    "WARNING (Case 3): Restart flow NOT generated. A DCLGEN "
                    "restart group was found, but the restart table is not "
                    "confirmed in the Sheet Mapping. Legacy IDMS restart flow "
                    "PRESERVED UNCHANGED. Add the restart table to the Sheet "
                    "Mapping to auto-convert."
                )
            else:
                # Case 2 / Case 4: restart DCLGEN itself was not resolved.
                diagnostics.append(
                    "WARNING (Case 2/4): Restart-table DCLGEN not resolved. "
                    "Legacy IDMS restart/control flow PRESERVED UNCHANGED and "
                    "must be redesigned manually. Add the restart table to the "
                    "DCLGEN inputs to auto-convert."
                )

        output = converted_cobol

        output = self.storage_include_manager.fix_malformed_sqlerror(
            output,
            diagnostics,
        )

        output = self.storage_include_manager.normalize_program_name(
            output,
            context,
            diagnostics,
        )

        output = self.storage_include_manager.ensure_working_storage(
            output,
            context,
            diagnostics,
        )

        output = self.storage_include_manager.ensure_date_working_storage(
            output,
            diagnostics,
        )

        output = self.storage_include_manager.ensure_dclgen_include(
            output,
            context,
            diagnostics,
        )

        output = self.storage_include_manager.ensure_referenced_dclgen_includes(
            output,
            diagnostics,
        )

        output = self.storage_include_manager.ensure_copybook_include(
            output,
            context,
            diagnostics,
        )

        output = self.main_flow_rewriter.replace_legacy_restart_main_flow(
            output,
            context,
            diagnostics,
        )

        output = self.restart_paragraph_manager.ensure_read_flat_file(
            output,
            context,
            diagnostics,
        )

        output = self.restart_paragraph_manager.ensure_restart_paragraphs(
            output,
            context,
            diagnostics,
        )

        output = self.business_sql_standardizer.standardize(
            output,
            context,
            diagnostics,
        )

        output = self.storage_include_manager.remove_legacy_restart_working_storage(
            output,
            diagnostics,
        )

        diagnostics.append(UPDATE_RESTART_DIAGNOSTICS["end"])

        return EnhancementResult(
            converted_cobol=output,
            diagnostics=diagnostics,
        )


__all__ = [
    "EnhancementResult",
    "UpdateProgramEnhancer",
]