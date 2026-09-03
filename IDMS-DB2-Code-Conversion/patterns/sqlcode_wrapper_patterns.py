from __future__ import annotations

import re

# Regex patterns for SQLCODE wrapper cleanup.
# Regex only. No business rules, program names, or hardcoded records.

# One-line MOVE <source> TO <target> (used to split into two body lines).
MOVE_TO_PATTERN = re.compile(
    r"^MOVE\s+(?P<source>.+?)\s+TO\s+(?P<target>.+?\.?)$",
    flags=re.IGNORECASE,
)