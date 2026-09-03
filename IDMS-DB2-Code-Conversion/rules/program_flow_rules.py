from __future__ import annotations

"""
Program flow analysis rules.

This module contains constants only.
No regex patterns, parser logic, analyzer logic, program names, DB2 table names,
DCLGEN names, or host variables belong here.
"""


PROGRAM_FLOW_ANALYSIS_RULES = [
    "Analyze COBOL flow for diagnostics only.",
    "Do not rewrite COBOL.",
    "Detect procedure paragraphs.",
    "Detect cursor-like IDMS operations from parsed operations.",
    "Detect output write statements.",
    "Detect basic date usage hints.",
    "Do not hardcode program names, DB2 tables, DB2 columns, DCLGEN groups, or host variables.",
]


CURSOR_OPERATIONS = {
    "OBTAIN_FIRST",
    "OBTAIN_NEXT",
    "FIND_FIRST",
}


WRITE_TOKENS = {
    "WRITE",
    "STORE",
    "MODIFY",
    "ERASE",
}


DATE_TOKENS = {
    "DATE",
    "TIME",
    "TIMESTAMP",
    "TS-",
}