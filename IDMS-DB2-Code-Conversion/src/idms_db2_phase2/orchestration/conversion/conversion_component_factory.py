# LOCATION: src/idms_db2_phase2/orchestration/conversion/conversion_component_factory.py
# ACTION: REPLACE ENTIRE FILE

from __future__ import annotations

from idms_db2_phase2.composers.cobol_cleanup_composer import CobolCleanupComposer
from idms_db2_phase2.composers.cobol_formatter import CobolFormatter
from idms_db2_phase2.composers.cursor_flow_composer import CursorFlowComposer
from idms_db2_phase2.composers.cursor_order_cleanup_composer import (
    CursorOrderCleanupComposer,
)
from idms_db2_phase2.composers.db2_date_comparison_composer import (
    Db2DateComparisonComposer,
)
from idms_db2_phase2.composers.final_cobol_fix_composer import (
    FinalCobolFixComposer,
    FinalCobolFixComposerConfig,
)
from idms_db2_phase2.composers.fixed_format_composer import FixedFormatComposer
from idms_db2_phase2.composers.manual_layout_composer import ManualLayoutComposer
from idms_db2_phase2.composers.manual_style_preserver import ManualStylePreserver
from idms_db2_phase2.composers.sqlcode_wrapper_cleanup_composer import (
    SqlcodeWrapperCleanupComposer,
)
from idms_db2_phase2.composers.update_program_feedback_composer import (
    UpdateProgramFeedbackComposer,
)
from idms_db2_phase2.composers.update_restart_skip_composer import (
    UpdateRestartSkipComposer,
)
from idms_db2_phase2.domain.models import ConversionInput
from idms_db2_phase2.generators.cursor_paragraph_generator import (
    CursorParagraphGenerator,
)
from idms_db2_phase2.generators.db2_infrastructure_generator import (
    Db2InfrastructureGenerator,
)
from idms_db2_phase2.generators.sql_error_generator import SqlErrorGenerator
from idms_db2_phase2.generators.sql_generator import SqlGenerator
from idms_db2_phase2.generators.timestamp_generator import TimestampGenerator
from idms_db2_phase2.repositories.copybook_repository import CopybookRepository
from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.repositories.lrf_repository import LrfRepository
from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.column_name_resolver import ColumnNameResolver
from idms_db2_phase2.resolvers.cursor_name_resolver import CursorNameResolver
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from idms_db2_phase2.resolvers.lrf_path_resolver import LrfPathResolver
from idms_db2_phase2.resolvers.record_context_resolver import RecordContextResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.transformers.cobol_transformer import CobolTransformer
from idms_db2_phase2.transformers.field_reference_rewriter import (
    FieldReferenceRewriter,
)
from idms_db2_phase2.transformers.idms_statement_transformer import (
    IdmsStatementTransformer,
)
from idms_db2_phase2.transformers.lrf_path_expander import LrfPathExpander
from rules.final_feedback_fix_rules import (
    DEFAULT_DB2_DATE_EXTERNAL_FORMAT,
    ORDER_BY_COLUMNS_IN_SELECT_DEFAULT,
)
from idms_db2_phase2.composers.record_materialisation_composer import (
    RecordMaterialisationComposer,
)
from idms_db2_phase2.composers.cursor_close_guarantee_composer import (
    CursorCloseGuaranteeComposer,
)


class ConversionComponentFactory:
    """Builds repositories, resolvers, generators, transformers, composers.

    CORRECTION - module imported where an instance was required
    -----------------------------------------------------------
    This file previously carried BOTH

        from idms_db2_phase2.resolvers import cursor_name_resolver
        from idms_db2_phase2.resolvers.cursor_name_resolver import CursorNameResolver

    and returned the first of those under the "cursor_name" key. That put a
    MODULE into the resolver map, so Db2InfrastructureGenerator failed at
    runtime with

        AttributeError: module 'idms_db2_phase2.resolvers.cursor_name_resolver'
        has no attribute 'cursor_name_from_table'

    The module import is removed. "cursor_name" now holds a constructed
    CursorNameResolver, like every other resolver in the map.

    LRF (Logical Record Facility)
    -----------------------------
    LRF metadata is OPTIONAL. With no subschema supplied, LrfRepository is
    empty, LrfPathResolver reports is_empty(), and LrfPathExpander returns
    the program source unchanged - so a program without logical records
    converts exactly as it did before LRF support existed.
    """

    # ------------------------------------------------------------------
    # Repositories
    # ------------------------------------------------------------------
    def _repositories(self, conversion_input: ConversionInput) -> dict[str, object]:
        return {
            "mapping": MappingRepository(conversion_input.sheet_mapping_rows),
            "dclgen": DclgenRepository(conversion_input.dclgen_columns),
            "copybook": CopybookRepository(conversion_input.copybook_fields),
            "lrf": LrfRepository(
                getattr(conversion_input, "logical_records", None) or []
            ),
        }

    # ------------------------------------------------------------------
    # Resolvers
    # ------------------------------------------------------------------
    def _resolvers(self, repositories: dict[str, object]) -> dict[str, object]:
        mapping_repository = repositories["mapping"]
        dclgen_repository = repositories["dclgen"]

        table_name_resolver = TableNameResolver(
            mapping_repository=mapping_repository,
            dclgen_repository=dclgen_repository,
        )
        column_name_resolver = ColumnNameResolver(
            mapping_repository=mapping_repository,
            dclgen_repository=dclgen_repository,
            table_name_resolver=table_name_resolver,
        )
        host_variable_resolver = HostVariableResolver(
            dclgen_repository=dclgen_repository,
            table_name_resolver=table_name_resolver,
        )
        record_context_resolver = RecordContextResolver(
            mapping_repository=mapping_repository,
            dclgen_repository=dclgen_repository,
        )

        # MUST be an instance. See the class docstring.
        cursor_name_resolver = CursorNameResolver()

        lrf_path_resolver = LrfPathResolver(
            lrf_repository=repositories.get("lrf"),
            mapping_repository=mapping_repository,
        )

        return {
            "table_name": table_name_resolver,
            "column_name": column_name_resolver,
            "host_variable": host_variable_resolver,
            "record_context": record_context_resolver,
            "cursor_name": cursor_name_resolver,
            "lrf_path": lrf_path_resolver,
        }

    # ------------------------------------------------------------------
    # Generators
    # ------------------------------------------------------------------
    def _generators(self, repositories, resolvers) -> dict[str, object]:
        sql_error_generator = SqlErrorGenerator()

        sql_generator = SqlGenerator(
            mapping_repository=repositories["mapping"],
            dclgen_repository=repositories["dclgen"],
            table_name_resolver=resolvers["table_name"],
            column_name_resolver=resolvers["column_name"],
            host_variable_resolver=resolvers["host_variable"],
        )
        db2_infrastructure_generator = Db2InfrastructureGenerator(
            table_name_resolver=resolvers["table_name"],
            column_name_resolver=resolvers["column_name"],
            host_variable_resolver=resolvers["host_variable"],
            cursor_name_resolver=resolvers["cursor_name"],
        )
        cursor_paragraph_generator = CursorParagraphGenerator(
            db2_infrastructure_generator=db2_infrastructure_generator,
            host_variable_resolver=resolvers["host_variable"],
            sql_error_generator=sql_error_generator,
        )
        timestamp_generator = TimestampGenerator(
            mapping_repository=repositories["mapping"],
            table_name_resolver=resolvers["table_name"],
            host_variable_resolver=resolvers["host_variable"],
        )

        return {
            "sql": sql_generator,
            "sql_error": sql_error_generator,
            "db2_infrastructure": db2_infrastructure_generator,
            "cursor_paragraph": cursor_paragraph_generator,
            "timestamp": timestamp_generator,
        }

    # ------------------------------------------------------------------
    # Transformers
    # ------------------------------------------------------------------
    def _transformers(self, repositories, resolvers, generators) -> dict[str, object]:
        idms_statement_transformer = IdmsStatementTransformer(
            sql_generator=generators["sql"],
            sql_error_generator=generators["sql_error"],
            table_name_resolver=resolvers["table_name"],
            cursor_name_resolver=resolvers["cursor_name"],
        )

        return {
            "idms_statement": idms_statement_transformer,
            "cobol": CobolTransformer(
                idms_statement_transformer=idms_statement_transformer
            ),
            "field_reference": FieldReferenceRewriter(
                mapping_repository=repositories["mapping"],
                table_name_resolver=resolvers["table_name"],
                host_variable_resolver=resolvers["host_variable"],
            ),
            # Runs FIRST in the pipeline. No-op when no LRF metadata or no
            # LRF syntax is present.
            "lrf_path_expander": LrfPathExpander(
                path_resolver=resolvers["lrf_path"],
            ),
        }

    # ------------------------------------------------------------------
    # Composers
    # ------------------------------------------------------------------
    def _composers(self, repositories, resolvers) -> dict[str, object]:
        composers: dict[str, object] = {}
        composers.update(self._formatting_composers())
        composers.update(self._cursor_composers())
        composers.update(self._cleanup_composers(repositories, resolvers))
        composers.update(self._update_composers(repositories, resolvers))
        composers.update(self._final_fix_composers())
        return composers

    def _formatting_composers(self) -> dict[str, object]:
        return {
            "formatter": CobolFormatter(),
            "fixed_format": FixedFormatComposer(),
            "manual_layout": ManualLayoutComposer(),
            "style_preserver": ManualStylePreserver(),
        }

    def _cursor_composers(self) -> dict[str, object]:

        return {
            "cursor_flow": CursorFlowComposer(),
            "cursor_close_guarantee": CursorCloseGuaranteeComposer(),
            "cursor_order_cleanup": CursorOrderCleanupComposer(),
            "sqlcode_cleanup": SqlcodeWrapperCleanupComposer(),
            "date_compare": Db2DateComparisonComposer(),
        }

    def _cleanup_composers(self, repositories, resolvers) -> dict[str, object]:
        return {
            "feedback_cleanup": CobolCleanupComposer(
                dclgen_repository=repositories["dclgen"],
            ),
            "update_restart_skip": UpdateRestartSkipComposer(),
            # Expands a whole-record MOVE into the record layout plus
            # field-by-field moves. Consumed by the FINISHING phase, not
            # by the content phase, because it needs sequenced lines.
            "record_materialisation": RecordMaterialisationComposer(
                mapping_repository=repositories["mapping"],
                table_name_resolver=resolvers["table_name"],
                host_variable_resolver=resolvers["host_variable"],
            ),
        }

    def _update_composers(self, repositories, resolvers) -> dict[str, object]:
        return {
            "update_program_feedback": UpdateProgramFeedbackComposer(
                mapping_repository=repositories["mapping"],
                dclgen_repository=repositories["dclgen"],
                table_name_resolver=resolvers["table_name"],
                host_variable_resolver=resolvers["host_variable"],
            ),
        }

    def _final_fix_composers(self) -> dict[str, object]:
        return {
            "final_feedback_fix": FinalCobolFixComposer(
                config=FinalCobolFixComposerConfig(
                    db2_date_external_format=DEFAULT_DB2_DATE_EXTERNAL_FORMAT,
                    require_order_by_columns_in_select=(
                        ORDER_BY_COLUMNS_IN_SELECT_DEFAULT
                    ),
                )
            ),
        }


__all__ = ["ConversionComponentFactory"]