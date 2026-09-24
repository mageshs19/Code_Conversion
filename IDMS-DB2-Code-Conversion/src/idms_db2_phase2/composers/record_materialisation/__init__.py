# LOCATION: src/idms_db2_phase2/composers/record_materialisation/__init__.py
# ACTION: REPLACE ENTIRE FILE
"""Whole-record MOVE materialisation.

    record_field_plan.py                 plan model + builder
    record_layout_generator.py           DATA DIVISION rendering
    record_move_generator.py             PROCEDURE DIVISION rendering
    record_line_utils.py                 fixed-format line I/O
    record_move_scanner.py               site discovery
    record_materialisation_guard.py      refusal decisions
    record_block_writer.py               line replacement
"""

from idms_db2_phase2.composers.record_materialisation.record_field_plan import (
    RecordFieldPlan,
    RecordMaterialisationPlan,
    RecordPlanBuilder,
)
from idms_db2_phase2.composers.record_materialisation.record_layout_generator import (
    RecordLayoutGenerator,
)
from idms_db2_phase2.composers.record_materialisation.record_move_generator import (
    RecordMoveGenerator,
)
from idms_db2_phase2.composers.record_materialisation.record_line_utils import (
    RecordLineUtils,
)
from idms_db2_phase2.composers.record_materialisation.record_move_scanner import (
    MoveSite,
    RecordMoveScanner,
    TargetSite,
)
from idms_db2_phase2.composers.record_materialisation.record_materialisation_guard import (
    RecordMaterialisationGuard,
    Refusal,
)
from idms_db2_phase2.composers.record_materialisation.record_block_writer import (
    RecordBlockWriter,
)

__all__ = [
    "MoveSite",
    "RecordBlockWriter",
    "RecordFieldPlan",
    "RecordLayoutGenerator",
    "RecordLineUtils",
    "RecordMaterialisationGuard",
    "RecordMaterialisationPlan",
    "RecordMoveGenerator",
    "RecordMoveScanner",
    "RecordPlanBuilder",
    "Refusal",
    "TargetSite",
]