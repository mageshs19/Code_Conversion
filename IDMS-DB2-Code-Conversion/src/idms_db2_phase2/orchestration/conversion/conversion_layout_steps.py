# LOCATION: src/idms_db2_phase2/orchestration/conversion/conversion_layout_steps.py
# ACTION: REPLACE ENTIRE FILE
"""Individual finishing passes of the IDMS->DB2 conversion.

One method per pass. Each takes the converted text, runs one composer,
drains that composer's diagnostics into the shared message list, and
returns the new text. No method knows about any other method, so the
ordering contract lives entirely in ConversionLayoutPipeline.

Deliberately NOT a mixin: it receives the composers and resolvers it
needs plus a message-collection callable, so every pass can be
constructed and tested without the component factory.

ORDERING CONTRACT (enforced by ConversionLayoutPipeline)

2.  ``apply_layout`` runs the formatter, manual layout, style preserver
    and fixed-format passes. ALL lines are sequenced here, BEFORE any
    commenting pass, so generator-inserted blocks carry a real sequence
    area and comment lines cannot be collapsed - they do not exist yet.

3.  ``OutputWriteParagraphComposer`` lifts the record-population body
    into its own WRITE paragraph. Runs AFTER fixed_format so every
    generated line can clone a real sequence area.

4.  ``LateDb2DateComposer`` re-runs the DB2 date and INITIALIZE passes.
    Those live inside ``feedback_cleanup`` and have already finished by
    the time step 3 moves the block into a brand new paragraph, so
    without this second run a DB2 date host field is moved straight into
    the output record, skipping the CCYYMMDD realignment. That is silent
    data corruption, not a formatting defect. Idempotent: a converted
    move carries no DCLGEN qualifier and cannot match again.

4b. ``RecordMaterialisationComposer`` expands every whole-record MOVE
    into a real layout plus field-by-field moves. Runs AFTER step 2 so
    generated lines can clone a real sequence area, BEFORE step 5 so the
    counter pass sees the final field list, and BEFORE steps 6 and 6b,
    which would otherwise comment the move as an undefined data-name.

5.  ``CounterDeclarationComposer`` declares every ``WS-NB-*-COUNT`` the
    PROCEDURE DIVISION increments but WORKING-STORAGE does not define,
    and appends the end-of-run totals before STOP RUN. It MUST run after
    step 3, which is what emits the increment, and BEFORE step 7 so the
    generated DISPLAY lines are indented with everything else.

6.  ``UnmappedRecordBlockComposer`` comments record-level blocks that
    have no usable DB2 column mapping. Runs after every content pass so
    it never comments code another pass still needs to read.

6b. ``StructuralSafetyComposer`` is the LAST guard before indentation.
    It comments whole-record references whose IDMS layout no longer
    exists, and statements left unreachable after a paragraph EXIT.
    It MUST run after step 6 - an unmapped-record block is commented
    first, so the safety pass never re-comments the same lines - and
    BEFORE step 7, so its comment lines are indented with everything
    else.

7.  ``ProcedureIndentNormalizer`` aligns every PROCEDURE DIVISION
    statement line to Area B.

8.  ``FinalSequenceResequencerService`` re-sequences ONLY columns 1-6
    and 73-80.

CORRECTION - step 4b was a silent no-op

    materialise_records returned the source unchanged and said nothing
    when the composer was absent, so an unwired feature was
    indistinguishable from a feature that ran and found nothing to do.
    The absence is now reported.
"""

from __future__ import annotations

from collections.abc import Callable

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
from idms_db2_phase2.composers.structural_safety_composer import (
    StructuralSafetyComposer,
)
from idms_db2_phase2.composers.unmapped_record_block_composer import (
    UnmappedRecordBlockComposer,
)
from idms_db2_phase2.services.final_sequence_resequencer_service import (
    FinalSequenceResequencerService,
)
from rules.record_materialisation_rules import (
    RECORD_MATERIALISATION_MESSAGES,
)


class ConversionLayoutSteps:
    """The finishing passes, each independently runnable."""

    def __init__(
        self,
        *,
        composers: dict,
        resolvers: dict,
        component_messages: Callable[[object], list[str]],
    ) -> None:
        self.composers = composers
        self.resolvers = resolvers
        self._component_messages = component_messages

    # =================================================================
    # 2. Layout and sequencing
    # =================================================================
    def apply_layout(
        self,
        *,
        converted_cobol: str,
        original_idms_text: str,
    ) -> str:
        converted_cobol = self.composers["formatter"].format(converted_cobol)
        converted_cobol = self.composers["manual_layout"].compose(
            converted_cobol
        )
        converted_cobol = self.composers["style_preserver"].preserve(
            original_text=original_idms_text,
            converted_text=converted_cobol,
        )
        # Fixed-format ALL lines BEFORE commenting so generator-inserted
        # blocks are sequenced and comment lines cannot be collapsed (they
        # do not exist yet at this point).
        return self.composers["fixed_format"].format(converted_cobol)

    # =================================================================
    # 3. Output write paragraph extraction
    # =================================================================
    def extract_output_write_paragraph(
        self,
        *,
        converted_cobol: str,
        validation_messages: list[str],
    ) -> str:
        """Lift the record-population body into its own WRITE paragraph.

        Replaces it with a PERFORM plus the output counter increment,
        matching the manual reference. Runs AFTER fixed_format so each
        generated line can clone a real sequence area.

        Refuses when the guard condition spans lines: cutting between the
        IF keyword and the end of its condition orphans the condition and
        the program will not compile.
        """
        composer = OutputWriteParagraphComposer()
        converted_cobol = composer.compose(converted_cobol)
        validation_messages.extend(self._component_messages(composer))
        return converted_cobol

    # =================================================================
    # 4. Late DB2 date / INITIALIZE re-run
    # =================================================================
    def apply_late_date_conversion(
        self,
        *,
        converted_cobol: str,
        validation_messages: list[str],
    ) -> str:
        """Re-run the date and INITIALIZE passes on the relocated block.

        Step 3 extracts the record-population body into a brand new
        WRITE paragraph AFTER feedback_cleanup has already finished, so
        without this second run a DB2 date host field is moved straight
        into the output record and skips the CCYYMMDD realignment. That
        is silent data corruption, not a formatting defect.

        Idempotent: a converted move carries no DCLGEN qualifier and
        cannot match again.
        """
        composer = LateDb2DateComposer()
        converted_cobol = composer.compose(converted_cobol)
        validation_messages.extend(self._component_messages(composer))
        return converted_cobol

    # =================================================================
    # 4b. IDMS record materialisation
    # =================================================================
    def materialise_records(
        self,
        *,
        converted_cobol: str,
        validation_messages: list[str],
    ) -> str:
        """Expand every whole-record MOVE into layout + field moves.

        Ordering:
            AFTER step 2, so generated lines can clone a real sequence area.
            BEFORE step 5, so the counter pass sees the final field list.
            BEFORE steps 6 and 6b, which would otherwise comment the move
            as an undefined data-name.

        CORRECTION - silent no-op.
        A build without the composer returned the source unchanged and
        said nothing, so an unwired feature was indistinguishable from a
        feature that ran and found nothing to do. The absence is now
        reported as a validation message.
        """
        composer = self.composers.get("record_materialisation")

        if composer is None:
            validation_messages.append(
                RECORD_MATERIALISATION_MESSAGES["composer_absent"]
            )
            return converted_cobol

        converted_cobol = composer.compose(converted_cobol)
        validation_messages.extend(self._component_messages(composer))
        return converted_cobol

    # =================================================================
    # 5. Counter declarations and end-of-run totals
    # =================================================================
    def declare_counters(
        self,
        *,
        converted_cobol: str,
        validation_messages: list[str],
    ) -> str:
        """Declare referenced counters and append end-of-run totals.

        Placement is safety-first: a record layout can never gain a field,
        so a dedicated 01 group is created when no work group is safe.
        """
        composer = CounterDeclarationComposer()
        converted_cobol = composer.compose(converted_cobol)
        validation_messages.extend(self._component_messages(composer))
        return converted_cobol

    # =================================================================
    # 6. Unmapped record blocks
    # =================================================================
    def comment_unmapped_blocks(
        self,
        *,
        converted_cobol: str,
        original_idms_text: str,
        validation_messages: list[str],
    ) -> str:
        composer = UnmappedRecordBlockComposer(
            table_name_resolver=self.resolvers["table_name"],
            column_name_resolver=self.resolvers["column_name"],
            original_idms_text=original_idms_text,
        )
        converted_cobol = composer.compose(converted_cobol)
        validation_messages.extend(self._component_messages(composer))
        return converted_cobol

    # =================================================================
    # 6b. Structural safety
    # =================================================================
    def apply_structural_safety(
        self,
        *,
        converted_cobol: str,
        original_idms_text: str,
        validation_messages: list[str],
    ) -> str:
        """Comment references the compiler would reject.

        Two guards, both COMMENT-ONLY:

          * a whole-record MOVE of an IDMS record whose copybook was
            removed - an undefined data-name,
          * an executable statement after a paragraph EXIT - unreachable
            and outside any paragraph.

        Nothing is deleted and no logic is rewritten, so a false positive
        costs a comment, never working code.
        """
        composer = StructuralSafetyComposer(
            original_idms_text=original_idms_text,
        )
        converted_cobol = composer.compose(converted_cobol)
        validation_messages.extend(self._component_messages(composer))
        return converted_cobol

    # =================================================================
    # 7. Procedure Division indentation
    # =================================================================
    def normalize_indentation(
        self,
        *,
        converted_cobol: str,
        validation_messages: list[str],
    ) -> str:
        normalizer = ProcedureIndentNormalizer()
        converted_cobol = normalizer.compose(converted_cobol)
        validation_messages.extend(self._component_messages(normalizer))
        return converted_cobol

    # =================================================================
    # 8. Final resequence
    # =================================================================
    @staticmethod
    def resequence(converted_cobol: str) -> str:
        """Re-sequence ONLY columns 1-6 and 73-80.

        Corrects the placeholder sequence numbers cloned by the
        extraction, counter and safety passes.
        """
        return FinalSequenceResequencerService().resequence(converted_cobol)


# ---------------------------------------------------------------------
# Backwards-compatible aliases for step 4.
#
# apply_late_date_conversion is the canonical name and is what
# ConversionLayoutPipeline.finish() calls. The aliases keep any older
# caller or test working without a second file having to change.
# ---------------------------------------------------------------------
ConversionLayoutSteps.reapply_db2_dates = (
    ConversionLayoutSteps.apply_late_date_conversion
)
ConversionLayoutSteps.apply_late_db2_dates = (
    ConversionLayoutSteps.apply_late_date_conversion
)
ConversionLayoutSteps.late_db2_dates = (
    ConversionLayoutSteps.apply_late_date_conversion
)


__all__ = ["ConversionLayoutSteps"]