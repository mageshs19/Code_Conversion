# LOCATION: patterns/fixed_format_wrap_patterns.py
# ACTION: CREATE NEW FILE

"""Fixed-format wrapping regex. Patterns only."""

from __future__ import annotations

import re

# MOVE <source> TO <target>, with an optional terminator.
MOVE_TO_PATTERN = re.compile(
    r"^MOVE\s+(?P<source>.+?)\s+TO\s+(?P<target>.+?)(?P<dot>\s*\.)?$",
    flags=re.IGNORECASE,
)

# A paragraph header on its own logical line.
PARAGRAPH_HEADER_PATTERN = re.compile(
    r"^[A-Z0-9][A-Z0-9-]*\.$",
    flags=re.IGNORECASE,
)

# Division and section headers, which also close a preceding sentence.
DIVISION_OR_SECTION_PATTERN = re.compile(
    r"^(?:[A-Z]+\s+DIVISION\b|[A-Z0-9][A-Z0-9-]*\s+SECTION\s*\.)",
    flags=re.IGNORECASE,
)