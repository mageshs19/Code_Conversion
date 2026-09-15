"""Controls which checks run. Edit this file only.

Drop a module in code_review/checks to ADD a check. List its id in
DISABLED_CHECKS to REMOVE it. There is no central list of class names to
maintain: code_review/engine/registry.py discovers checks with pkgutil.
"""

from __future__ import annotations

# Empty tuple means: run everything the registry discovers.
# Populate it only to run a deliberate subset, for example during triage.
ENABLED_CHECKS: tuple[str, ...] = ()

# List ids here to switch a check off without deleting its file.
DISABLED_CHECKS: frozenset[str] = frozenset()

# Report order. Any check not listed falls back to its own ORDER attribute,
# then to its id, so a newly dropped-in check still sorts sensibly before
# anyone edits this file.
CHECK_ORDER: tuple[str, ...] = (
    # Layout and structure
    "CHK-01", "CHK-06", "CHK-07",
    # DB2 infrastructure and error routing
    "CHK-02", "CHK-05", "CHK-08",
    # Conversion completeness
    "CHK-03", "CHK-04", "CHK-09", "CHK-11",
    # Cursor family
    "CHK-12", "CHK-13", "CHK-14", "CHK-15",
    # Update family
    "CHK-10", "CHK-16", "CHK-17", "CHK-18",
    # Restart family
    "CHK-19", "CHK-20", "CHK-21",
    # Authority family
    "CHK-22", "CHK-23", "CHK-24", "CHK-25",
)


# A failure at any of these severities makes the verdict REJECTED.
# Severities are Critical, Major, Minor. See open decision D-5.
BLOCKING_SEVERITIES: tuple[str, ...] = ("Critical",)

# Maximum evidence lines recorded per criterion.
EVIDENCE_LIMIT = 10


