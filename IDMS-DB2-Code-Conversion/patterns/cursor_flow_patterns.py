"""
Cursor flow regex patterns.

Regex patterns belong in patterns/, not in composer or service classes.
These patterns are shared by the cursor flow composer helper classes.
"""

import re

PERFORM_CURSOR_PATTERN = re.compile(
    r"^\s*PERFORM\s+"
    r"(?P<number>\d{3})-"
    r"(?P<operation>OPEN|FETCH|CLOSE)-"
    r"(?P<cursor>[A-Z0-9-]+)"
    r"\.?\s*$",
    flags=re.IGNORECASE,
)

PERFORM_BUSINESS_PATTERN = re.compile(
    r"^\s*PERFORM\s+"
    r"(?P<paragraph>[A-Z0-9][A-Z0-9-]*)"
    r"\.?\s*$",
    flags=re.IGNORECASE,
)

UNTIL_SQLCODE_100_PATTERN = re.compile(
    r"^\s*UNTIL\s+SQLCODE\s*=\s*100\.?\s*$",
    flags=re.IGNORECASE,
)

CURSOR_PARAGRAPH_HEADER_PATTERN = re.compile(
    r"^\s*"
    r"(?P<number>\d{3})-"
    r"(?P<operation>OPEN|FETCH|CLOSE)-"
    r"(?P<cursor>[A-Z0-9-]+)"
    r"\.\s*$",
    flags=re.IGNORECASE,
)

ANY_PARAGRAPH_HEADER_PATTERN = re.compile(
    r"^\s*[A-Z0-9][A-Z0-9-]*\.\s*$",
    flags=re.IGNORECASE,
)

WHEN_ZERO_PATTERN = re.compile(
    r"^\s*WHEN\s+ZERO\s*$",
    flags=re.IGNORECASE,
)

CONTINUE_PATTERN = re.compile(
    r"^\s*CONTINUE\.?\s*$",
    flags=re.IGNORECASE,
)

CONVERTED_OBTAIN_NEXT_COMMENT_PATTERN = re.compile(
    r"^\s*\*\s*DB2:\s*Converted\s+OBTAIN\s+NEXT\b",
    flags=re.IGNORECASE,
)

CONVERTED_OBTAIN_COMMENT_PATTERN = re.compile(
    r"^\s*\*\s*DB2:\s*Converted\s+OBTAIN\b",
    flags=re.IGNORECASE,
)