# LOCATION: code_review/engine/sql_location.py
# ACTION: CREATE NEW FILE

"""Shared SQL-LOCATION detection for CHK-05, CHK-09, CHK-10 and CHK-20.

The manual reference program moves the bare paragraph number:

    MOVE 710                 TO SQL-LOCATION

The quoted paragraph-name form is equally valid and is what the restart
template emits:

    MOVE '710-OPEN-DZBEFFC1' TO SQL-LOCATION

Both must be recognised. Testing only for a "MOVE '" prefix makes the
manual reference itself fail CHK-09.05, CHK-10.05 and CHK-20.07, which is
by definition a false positive.

Read-only. Knows nothing about programs, cursors, tables or host variables.
"""

from __future__ import annotations

import re

from code_review.engine import sql_blocks as sql
from code_review.standards import cobol_standards as std

# MOVE <bare-number|'quoted-literal'> TO SQL-LOCATION
# The terminator is optional: the site standard closes a paragraph with a
# lone period line, so the MOVE itself carries no period.
MOVE_SQL_LOCATION = re.compile(
    r"^MOVE\s+(?:'[^']*'|\d+)\s+TO\s+"
    + re.escape(std.SQL_LOCATION_FIELD)
    + r"\s*\.?$"
)


def is_location_move(line: str) -> bool:
    """True when the logical line sets SQL-LOCATION in an accepted form."""
    return bool(MOVE_SQL_LOCATION.match(sql.norm(line)))


def set_before(view, block, lookback: int | None = None) -> bool:
    """True when SQL-LOCATION is set within the look-back window of a block."""
    window = sql.lines_before(
        view,
        block,
        std.SQL_LOCATION_LOOKBACK if lookback is None else lookback,
    )
    return any(is_location_move(line) for line in window)