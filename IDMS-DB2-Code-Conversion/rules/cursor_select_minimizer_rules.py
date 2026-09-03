from __future__ import annotations

"""
Rules for cursor SELECT minimization.

This module contains constants only.
No regex patterns, service logic, parser logic, cursor names, table names,
columns, or host variables belong here.
"""


CURSOR_SELECT_MINIMIZER_RULES = [
    "Remove columns selected only for ORDER BY when safe.",
    "Do not hardcode cursor names, table names, columns, or host variables.",
    "Keep SELECT and FETCH INTO synchronized by position.",
    "Do not treat SQL keywords as selected columns.",
    "Normalize commas only inside SELECT item and FETCH INTO scopes.",
]


SQL_NON_COLUMN_KEYWORDS = {
    "SELECT",
    "FROM",
    "WHERE",
    "ORDER",
    "ORDER BY",
    "GROUP",
    "GROUP BY",
    "HAVING",
    "FOR",
    "FOR READ ONLY",
    "INTO",
    "END-EXEC",
    "EXEC SQL",
}


SELECT_FIRST_ITEM_BODY_PREFIX = "        "
SELECT_NEXT_ITEM_BODY_PREFIX = "       , "
FETCH_HOST_BODY_PREFIX = "        "