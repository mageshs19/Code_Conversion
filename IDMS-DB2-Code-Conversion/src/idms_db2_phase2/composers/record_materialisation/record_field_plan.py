# LOCATION: src/idms_db2_phase2/composers/record_materialisation/record_field_plan.py
# ACTION: REPLACE ENTIRE FILE
"""Back-compatible import point for the record plan model.

The model was split so no file exceeds a reviewable size:

    record_field.py          RecordFieldPlan      shape + policy
    record_plan.py           RecordMaterialisationPlan  views + sizes
    record_row_reader.py     Sheet Mapping row -> field
    record_host_resolver.py  table / group / host lookups
    record_plan_builder.py   orchestration

Several modules already import the three public names from here
(record_layout_generator, record_move_generator, the package __init__),
so this module keeps working as their import point. Nothing else had to
change.
"""

from __future__ import annotations

from idms_db2_phase2.composers.record_materialisation.record_field import (
    COMP_3_SYMBOL,
    DEFAULT_LEVEL,
    RecordFieldPlan,
)
from idms_db2_phase2.composers.record_materialisation.record_host_resolver import (
    RecordHostResolver,
)
from idms_db2_phase2.composers.record_materialisation.record_plan import (
    RecordMaterialisationPlan,
)
from idms_db2_phase2.composers.record_materialisation.record_plan_builder import (
    RecordPlanBuilder,
)
from idms_db2_phase2.composers.record_materialisation.record_row_reader import (
    RecordRowReader,
)

__all__ = [
    "COMP_3_SYMBOL",
    "DEFAULT_LEVEL",
    "RecordFieldPlan",
    "RecordHostResolver",
    "RecordMaterialisationPlan",
    "RecordPlanBuilder",
    "RecordRowReader",
]