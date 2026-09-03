from __future__ import annotations

import re

# Regex patterns shared by the batch/update/retrieval runners.
# No business rules, no runtime logic, no hardcoded program/record names.

# Matches a COBOL COPY statement and captures the copybook/record name.
COPY_NAME_PATTERN = re.compile(
    r"\bCOPY\s+([A-Z0-9-]+)\b",
    flags=re.IGNORECASE,
)