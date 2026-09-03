from __future__ import annotations

"""
Field usage analysis rules.

This module contains rule constants only.
No regex patterns, parser logic, analyzer logic, program names, DB2 table names,
DCLGEN names, or host variables belong here.
"""


FIELD_USAGE_ANALYSIS_RULES = [
    "Detect COBOL field usage without rewriting COBOL.",
    "Track IDMS qualified field references by mapped record.",
    "Track DCLGEN host references by resolved DCLGEN group context.",
    "Track MOVE source and target fields separately.",
    "Track condition fields from IF, WHEN, UNTIL, and EVALUATE statements.",
    "Do not hardcode program names, DB2 tables, DB2 columns, or host variables.",
]


DCLGEN_GROUP_PREFIX = "DCL"


OUTPUT_TARGET_PREFIXES = (
    "UIT-",
)