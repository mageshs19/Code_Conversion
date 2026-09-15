# LOCATION: src/idms_db2_phase2/composers/cobol_cleanup_composer.py
# ACTION: REPLACE ENTIRE FILE

"""
COBOL post-conversion cleanup composer.

Applies only safe post-conversion COBOL cleanup passes:
- Remove residual IDMS conversion comment noise (+ redundant CONTINUE).
- Replace residual IDMS ERROR-STATUS loop control with DB2 flag control.
- Declare SW-STATUS-D only when needed.
- Add SW-STATUS-D early stop to nested child cursor fetch loops.
- Move a guarded output write out of the child-row paragraph to the parent
  paragraph, after the child cursor CLOSE.
- Add INITIALIZE before output-record population.
- Convert DB2 date host fields to output numeric date format before WRITE.
- Ensure DCLGEN INCLUDE exists when a DCLGEN group is referenced.
- Close any paragraph sentence left unterminated by an earlier pass.

No program names, table names, record names, or business-specific fields
are hardcoded. Exposes the accumulated messages list for conversion_service.

Pass ordering notes
-------------------
`OutputWritePlacementCleanup` must run AFTER `ChildFetchEarlyStopCleanup`,
because it reads the early-stop flag from the child fetch loop to decide
whether the relocated block needs the `IF NOT SW-STATUS-D = 'Y'` guard, and
BEFORE `InitializeBeforeOutputCleanup` and `Db2DateOutputCleanup`, so those
two passes see the write block in its final position.

`ParagraphTerminatorCleanup` runs LAST. Any pass that inserts or lifts a
block can leave a paragraph ending on a bare scope terminator, which makes
the sentence run into the next paragraph header and the compiler reject the
program. This pass is the final guard for that.
"""

from idms_db2_phase2.composers.cleanup.child_fetch_early_stop_cleanup import (
    ChildFetchEarlyStopCleanup,
)
from idms_db2_phase2.composers.cleanup.cleanup_message_collector import (
    CleanupMessageCollector,
)
from idms_db2_phase2.composers.cleanup.cobol_cleanup_line_utils import (
    CobolCleanupLineUtils,
)
from idms_db2_phase2.composers.cleanup.db2_date_output_cleanup import (
    Db2DateOutputCleanup,
)
from idms_db2_phase2.composers.cleanup.dclgen_include_cleanup import (
    DclgenIncludeCleanup,
)
from idms_db2_phase2.composers.cleanup.error_status_flag_cleanup import (
    ErrorStatusFlagCleanup,
)
from idms_db2_phase2.composers.cleanup.initialize_before_output_cleanup import (
    InitializeBeforeOutputCleanup,
)
from idms_db2_phase2.composers.cleanup.output_write_placement_cleanup import (
    OutputWritePlacementCleanup,
)
from idms_db2_phase2.composers.cleanup.paragraph_terminator_cleanup import (
    ParagraphTerminatorCleanup,
)
from idms_db2_phase2.composers.cleanup.residual_idms_comment_cleanup import (
    ResidualIdmsCommentCleanup,
)
from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository


class CobolCleanupComposer:
    def __init__(
        self,
        dclgen_repository: DclgenRepository,
    ) -> None:
        self.dclgen_repository = dclgen_repository
        self._collector = CleanupMessageCollector()
        line_utils = CobolCleanupLineUtils()

        self._residual_comment = ResidualIdmsCommentCleanup(
            messages=self._collector,
            line_utils=line_utils,
        )
        self._dclgen_include = DclgenIncludeCleanup(
            dclgen_repository=dclgen_repository,
            messages=self._collector,
            line_utils=line_utils,
        )
        self._error_status = ErrorStatusFlagCleanup(
            messages=self._collector,
            line_utils=line_utils,
        )
        self._child_fetch = ChildFetchEarlyStopCleanup(
            messages=self._collector,
            line_utils=line_utils,
        )
        self._output_write_placement = OutputWritePlacementCleanup(
            messages=self._collector,
            line_utils=line_utils,
        )
        self._initialize_output = InitializeBeforeOutputCleanup(
            messages=self._collector,
            line_utils=line_utils,
        )
        self._db2_date_output = Db2DateOutputCleanup(
            messages=self._collector,
            line_utils=line_utils,
        )
        self._paragraph_terminator = ParagraphTerminatorCleanup(
            messages=self._collector,
            line_utils=line_utils,
        )

    @property
    def messages(self) -> list[str]:
        return self._collector.messages

    def compose(self, text: str) -> str:
        self._collector.reset()
        output = str(text or "")

        if not output.strip():
            return output

        # Category G: strip residual IDMS comment noise first.
        output = self._residual_comment.remove_residual_idms_comments(output)

        output = self._dclgen_include.apply(output)
        output = self._error_status.replace_error_status_with_flag(output)
        output = self._error_status.ensure_sw_status_d_declaration(output)
        output = self._child_fetch.ensure_child_fetch_early_stop(output)

        # Must follow the early-stop pass: the guard around the relocated
        # block is derived from the child fetch loop condition.
        output = (
            self._output_write_placement
            .move_output_write_after_child_loop(output)
        )

        output = (
            self._initialize_output
            .ensure_initialize_before_output_population(output)
        )
        output = self._db2_date_output.convert_db2_date_moves_to_output_dates(
            output
        )

        # Final guard: no paragraph may end on an unterminated sentence.
        output = self._paragraph_terminator.ensure_paragraph_termination(
            output
        )

        return output.rstrip() + "\n"