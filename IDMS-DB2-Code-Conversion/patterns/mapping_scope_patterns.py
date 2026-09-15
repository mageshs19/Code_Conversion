# LOCATION: patterns/mapping_scope_patterns.py
# ACTION: CREATE NEW FILE

"""Mapping scope regex patterns. Patterns only."""

from __future__ import annotations

import re

# Trailing table qualifier on a mapping validation message:
#   Mapping validation: DB2 column mapping is missing. Table=DZ01FFTB
MESSAGE_TABLE_PATTERN = re.compile(
    r"\bTable\s*=\s*(?P<table>[A-Z0-9_]+)\b",
    flags=re.IGNORECASE,
)

# A record or table name token inside COBOL source.
SOURCE_TOKEN_PATTERN = re.compile(
    r"[A-Z][A-Z0-9_-]{2,}",
    flags=re.IGNORECASE,
)