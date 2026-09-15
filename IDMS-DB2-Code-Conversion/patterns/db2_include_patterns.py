"""DB2 INCLUDE scanning patterns.

Patterns only. No rules, no layout constants.

Both emitted shapes must be recognised, because duplicate detection that
sees only one of them is what produced DZBFARTV twice:

    EXEC SQL INCLUDE DZBFARTV END-EXEC.

    EXEC SQL
      INCLUDE DZBFARTV
    END-EXEC.
"""

from __future__ import annotations

import re

# The single-line form, complete on one logical line.
INCLUDE_SINGLE_PATTERN = re.compile(
    r"^EXEC\s+SQL\s+INCLUDE\s+(?P<name>[A-Z0-9][A-Z0-9_-]*)\s+END-EXEC\s*\.?$",
    flags=re.IGNORECASE,
)

# The INCLUDE body line of the three-line block form.
INCLUDE_BODY_PATTERN = re.compile(
    r"^INCLUDE\s+(?P<name>[A-Z0-9][A-Z0-9_-]*)\s*\.?$",
    flags=re.IGNORECASE,
)

# Any INCLUDE name, whichever shape carries it.
INCLUDE_NAME_PATTERN = re.compile(
    r"\bINCLUDE\s+(?P<name>[A-Z0-9][A-Z0-9_-]*)\b",
    flags=re.IGNORECASE,
)

EXEC_SQL_OPEN_PATTERN = re.compile(
    r"^EXEC\s+SQL\b",
    flags=re.IGNORECASE,
)

END_EXEC_PATTERN = re.compile(
    r"^END-EXEC\s*\.?$",
    flags=re.IGNORECASE,
)

# A DCLGEN host group reference. Owned here so every consumer can rely on
# the 'group' capture name.
DCLGEN_GROUP_PATTERN = re.compile(
    r"\b(?P<group>DCL[A-Z0-9_-]+)\b",
    flags=re.IGNORECASE,
)