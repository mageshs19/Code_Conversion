# LOCATION: rules/db2_include_rules.py
# ACTION: CREATE NEW FILE

"""DB2 INCLUDE emission rules.

Constants only. No regex, no runtime logic, no program / record / table
names.

WHY THIS EXISTS
---------------
Three components emitted EXEC SQL INCLUDE independently:

  InfrastructureBlockBuilder   3-line block, Area B
  DclgenIncludeCleanup         3-line block, 1 space
  StorageWsInjector            single line,  1 space

Two shapes and no shared duplicate detection. The update injector looked
for the SINGLE-LINE form, did not recognise the BLOCK form already
emitted upstream, and injected DZBFARTV a second time. A duplicated
DCLGEN include duplicates every data-name in the group, which the
compiler rejects.

Every emitter now renders through IncludeRenderer using these constants,
so the shape and the indent are decided in one place.
"""

from __future__ import annotations

# =====================================================================
# Canonical form
# =====================================================================
# True  -> EXEC SQL INCLUDE SQLCA END-EXEC.        (one line)
# False -> EXEC SQL / INCLUDE SQLCA / END-EXEC.    (three lines)
#
# The COBOL team's manual reference uses the single-line form for
# includes and the block form for cursor declarations.
INCLUDE_SINGLE_LINE = True

INCLUDE_SINGLE_TEMPLATE = "EXEC SQL INCLUDE {name} END-EXEC."
INCLUDE_BLOCK_OPEN = "EXEC SQL"
INCLUDE_BLOCK_BODY_TEMPLATE = "INCLUDE {name}"
INCLUDE_BLOCK_CLOSE = "END-EXEC."

# =====================================================================
# Indentation, relative to column 8
# =====================================================================
# CHK-06.07 requires at least 4 body spaces, i.e. physical column 12.
IND_INCLUDE = "    "        # column 12
IND_INCLUDE_BODY = "      "  # column 14

# =====================================================================
# Infrastructure includes
# =====================================================================
# Never treated as DCLGEN table includes, and never auto-injected as one.
INFRASTRUCTURE_INCLUDES = frozenset(
    {"SQLCA", "SQLERRWS", "SQLERROR", "GEN"}
)

# =====================================================================
# Diagnostics
# =====================================================================
INCLUDE_MESSAGES = {
    "rendered": "DB2 includes: rendered {count} include statement(s).",
    "skipped_duplicate": (
        "DB2 includes: {name} is already included; not injected again."
    ),
    "injected": "DB2 includes: injected missing include {name}.",
    "removed_duplicate": (
        "DB2 includes: removed {count} duplicate include statement(s) "
        "for {name}."
    ),
}