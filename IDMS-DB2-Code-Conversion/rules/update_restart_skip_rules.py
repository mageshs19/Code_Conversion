from __future__ import annotations

# Update restart/control skip cleanup constants. Constants only.
# No regex, no runtime logic, no program/record/table names.

# Markers that indicate a generated missing-mapping block.
MISSING_MAPPING_MARKERS = (
    "CONVERSION SKIPPED",
    "MISSING SHEET MAPPING",
    "MISSING DCLGEN",
    "MISSING SELECT",
    "MISSING INSERT",
    "MISSING UPDATE",
    "MISSING DELETE",
    "MISSING MAPPING",
    "MISSING KEY COLUMN METADATA",
    "INCOMPLETE CONSERVATIVE UPDATE METADATA",
    "MISSING INSERT COLUMNS",
)

# Substrings that identify a restart/control-like record name.
RESTART_CONTROL_HINTS = (
    "RECAB",
    "RESTART",
    "RST",
    "CONTROL",
    "CTRL",
    "CHECKPOINT",
    "CHKPT",
)

# Generated replacement comment block for an unmapped restart/control record.
REPLACEMENT_BLOCK_TEMPLATES = (
    "* DB2: IDMS record {record} was not converted automatically.",
    "* DB2: Missing Sheet Mapping and DCLGEN metadata.",
    "* DB2: Restart/control logic requires manual DB2 redesign.",
    "CONTINUE.",
)

# Advisory message (suppressed by default; the update post-process now
# generates the real DB2 restart-table flow, so this advisory is obsolete).
EMIT_MANUAL_REDESIGN_MESSAGE = False
MANUAL_REDESIGN_MESSAGE_TEMPLATE = (
    "Update restart/control skip: restart/control record "
    "{record_name} requires manual DB2 redesign."
)