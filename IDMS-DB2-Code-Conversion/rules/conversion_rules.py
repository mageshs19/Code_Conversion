"""
General IDMS to DB2 conversion rules.
"""


CONVERSION_RULES = [
    "Preserve original COBOL business flow.",
    "Replace IDMS database operations with DB2-compatible SQL logic.",
    "Do not fabricate DB2 SQL when Sheet Mapping metadata is missing.",
    "When mapping metadata is missing, generate a clear DB2 conversion-skipped comment.",
    "When removing executable PROCEDURE DIVISION IDMS code, add CONTINUE.",
]


MISSING_MAPPING_RULES = [
    "FFRECAB conversion requires Sheet Mapping and DCLGEN metadata.",
    "If Sheet Mapping entry is missing, conversion must be skipped with a clear comment.",
    "Missing Sheet Mapping metadata is an input-data blocker, not a Python logic failure.",
]

# LOCATION: rules/conversion_rules.py
# ACTION: REPLACE the Option B constants (find UNMAPPED_RECORD_MARKER_TEMPLATE
#         and COMMENTED_IDMS_LINE_PREFIX, replace with these)

# --- Option B: unmapped-record handling (keep-and-comment) ---
# Marker text is deliberately distinct (DB2-KEEP, not "DB2:") so the
# residual-comment cleanup (Category G) never matches and strips it.
UNMAPPED_RECORD_MARKER_TEMPLATE = (
    "*DB2-KEEP: {record} has no usable DB2 column mapping "
    "- map this IDMS logic manually."
)

# Prefix used to comment out an un-convertible IDMS verb line (kept visible).
COMMENTED_IDMS_LINE_PREFIX = "*DB2-KEEP  "