# LOCATION: manual_conventions/paragraph_numbering_conventions.py
# ACTION: CREATE NEW FILE (documentation-only; NOT wired into the converter)

"""
Paragraph numbering conventions (DEFERRED - pending COBOL team review).

Observed in manual DB2 rewrites. NOT applied by the automated converter,
which preserves original paragraph names per the business-flow rule.

These are documented here so the team can later decide on a standard scheme.
Do NOT import these into active conversion logic until approved.
"""

from __future__ import annotations

# Example scheme observed in one manual rewrite (NOT authoritative).
# Left as data for future discussion only.
OBSERVED_PARAGRAPH_NUMBERING = {
    "main_process": "1000-",     # e.g. VERWERKING -> 1000-VERWERKING
    "commit_process": "800-",    # e.g. 800-PROCESS-COMMIT
    "restart_control": "700-",   # e.g. 700-RESTART-CONTROL
    "timestamp": "820000-",      # e.g. 820000-GET-TIMESTAMP
}

DEFERRED_NOTE = (
    "Paragraph renumbering restructures business flow and is not an IDMS->DB2 "
    "conversion. Requires COBOL team agreement on a consistent scheme before "
    "any automation."
)