# LOCATION: src/idms_db2_phase2/composers/counter_declaration/__init__.py
# ACTION: CREATE NEW FILE
"""Placement and rendering helpers for generated row counters.

CounterDeclarationComposer decides WHAT to declare.
This package decides WHERE it goes and HOW it is rendered.
"""

from idms_db2_phase2.composers.counter_declaration.counter_anchor import (
    CounterAnchor,
    CounterAnchorFinder,
)
from idms_db2_phase2.composers.counter_declaration.counter_anchor_resolver import (
    CounterAnchorResolver,
)
from idms_db2_phase2.composers.counter_declaration.counter_line_factory import (
    CounterLineFactory,
)
from idms_db2_phase2.composers.counter_declaration.counter_totals_writer import (
    CounterTotalsWriter,
)

__all__ = [
    "CounterAnchor",
    "CounterAnchorFinder",
    "CounterAnchorResolver",
    "CounterLineFactory",
    "CounterTotalsWriter",
]