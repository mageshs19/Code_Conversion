# LOCATION: src/idms_db2_phase2/composers/late_db2_date_composer.py
# ACTION: CREATE NEW FILE

"""Late DB2 date output conversion.

Re-runs Db2DateOutputCleanup after the output write block has reached its
FINAL location.

Why a second run is needed
--------------------------
Db2DateOutputCleanup lives inside CobolCleanupComposer. Its documented
ordering places it after OutputWritePlacementCleanup so it can see the
write block in its final position.

That held while the block merely moved between paragraphs. It no longer
holds: OutputWriteParagraphComposer now EXTRACTS the block into a new
WRITE-<record> paragraph much later in the pipeline. The date converter
has already finished by then, so a DB2 date host field is moved straight
into the output record without the CCYYMMDD realignment:

    MOVE DA-UBSECIS-479BEFF OF DCLDZBEFFTV TO UIT-DA-UBSEC

UIT-DA-UBSEC then receives the raw DB2 external date form rather than the
numeric form the downstream file expects. That is silent data corruption,
not a formatting defect.

Idempotence
-----------
A second run is safe. The converter only matches a MOVE whose source is a
DB2 date host qualified by a DCLGEN group. After conversion the move
reads

    MOVE DA-CCYYMMDD-R TO UIT-DA-UBSEC

which carries no DCLGEN qualifier and therefore cannot match again.
"""

from __future__ import annotations

from idms_db2_phase2.composers.cleanup.cleanup_message_collector import (
    CleanupMessageCollector,
)
from idms_db2_phase2.composers.cleanup.db2_date_output_cleanup import (
    Db2DateOutputCleanup,
)
from idms_db2_phase2.composers.cleanup.initialize_before_output_cleanup import (
    InitializeBeforeOutputCleanup,
)


class LateDb2DateComposer:
    """Applies the date and INITIALIZE passes to the relocated block."""

    def __init__(self) -> None:
        self.collector = CleanupMessageCollector()
        self.date_cleanup = Db2DateOutputCleanup(messages=self.collector)
        self.initialize_cleanup = InitializeBeforeOutputCleanup(
            messages=self.collector
        )
        self.messages: list[str] = []

    def compose(self, text: str) -> str:
        self.messages = []

        if not text:
            return ""

        self.collector.reset()
        output = str(text)

        output = self.initialize_cleanup.ensure_initialize_before_output_population(
            output
        )
        output = self.date_cleanup.convert_db2_date_moves_to_output_dates(
            output
        )

        self.messages = list(self.collector.messages)
        return output.rstrip() + "\n"