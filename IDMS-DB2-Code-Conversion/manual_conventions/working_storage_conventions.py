# LOCATION: manual_conventions/working_storage_conventions.py
# ACTION: CREATE NEW FILE (documentation-only)

"""
Working-storage conventions (DEFERRED - pending COBOL team review).

Observed additions in manual rewrites that the converter does NOT generate,
because they add new business logic rather than converting IDMS access.
"""

from __future__ import annotations

# Counters observed in a manual rewrite (NOT auto-generated).
OBSERVED_PROCESSING_COUNTERS = [
    "WS-TELLER",
    "WS-NB-INPUT-UPD-I",
    "WS-NB-BFAR-UPD-I",
]

# EOF flag style observed (88-level instead of raw switch).
OBSERVED_EOF_FLAG_STYLE = {
    "group": "WS-SWITCHES",
    "field": "SW-<record>",
    "conditions": ["<record>-NOT-EOF VALUE 'N'", "<record>-EOF VALUE 'Y'"],
}

DEFERRED_NOTE = (
    "Processing counters and 88-level EOF flags are program-design choices, "
    "not IDMS->DB2 conversions. Requires COBOL team sign-off; #2 changes "
    "behavior, #6 is style only."
)