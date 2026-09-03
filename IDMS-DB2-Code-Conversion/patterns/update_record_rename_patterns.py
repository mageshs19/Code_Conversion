from __future__ import annotations

import re

# Regex patterns for update-program input-record rename.
#
# Regex only. No business rules, program names, record names, DB2 tables,
# DCLGEN names, copybook names, or host variables.

# A COPY statement for a specific record (name injected via .format with
# re.escape). Matches "COPY <name>" and optional trailing period.
COPY_RECORD_PATTERN_TEMPLATE = r"\bCOPY\s+{name}\b\.?"

# A whole-word occurrence of a specific record name (name injected via
# .format with re.escape). Word boundaries prevent partial matches.
WORD_RECORD_PATTERN_TEMPLATE = r"(?<![A-Z0-9-]){name}(?![A-Z0-9-])"