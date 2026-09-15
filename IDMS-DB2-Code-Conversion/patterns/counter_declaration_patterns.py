# LOCATION: patterns/counter_declaration_patterns.py
# ACTION: CREATE NEW FILE

"""Counter declaration regex patterns.

This file must contain regex patterns only.

No token lists, business rules, conversion rules or layout constants.
Patterns are matched against an already-stripped logical line.
"""

from __future__ import annotations

import re

# An increment of a generated row counter.
#   ADD 1 TO WS-NB-OUTPUT-COUNT
COUNTER_INCREMENT_PATTERN = re.compile(
    r"^ADD\s+\d+\s+TO\s+(?P<name>WS-NB-[A-Z0-9][A-Z0-9-]*)\s*\.?$",
    flags=re.IGNORECASE,
)

# Any COBOL data description entry, used to collect declared names.
DATA_ENTRY_PATTERN = re.compile(
    r"^(?P<level>\d{2})\s+(?P<name>[A-Z0-9][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)

# An 01-level group header.
GROUP_HEADER_PATTERN = re.compile(
    r"^01\s+(?P<name>[A-Z0-9][A-Z0-9-]*)\s*\.$",
    flags=re.IGNORECASE,
)

# A subordinate entry, i.e. any level other than 01 / 77 / 88.
SUBORDINATE_ENTRY_PATTERN = re.compile(
    r"^(?P<level>0[2-9]|[1-4][0-9]|49)\s+(?P<name>[A-Z0-9][A-Z0-9-]*)\b",
    flags=re.IGNORECASE,
)

WORKING_STORAGE_PATTERN = re.compile(
    r"^WORKING-STORAGE\s+SECTION\s*\.$",
    flags=re.IGNORECASE,
)

SECTION_OR_DIVISION_PATTERN = re.compile(
    r"^([A-Z0-9-]+\s+SECTION|[A-Z]+\s+DIVISION)\b",
    flags=re.IGNORECASE,
)

STOP_RUN_PATTERN = re.compile(
    r"^STOP\s+RUN\s*\.?$",
    flags=re.IGNORECASE,
)