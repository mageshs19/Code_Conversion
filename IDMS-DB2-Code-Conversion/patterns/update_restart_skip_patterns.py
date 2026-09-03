from __future__ import annotations

import re

# Regex patterns for update restart/control skip cleanup.
# Regex only. No business rules, program names, or hardcoded records.

CONVERTED_FOR_PATTERN = re.compile(
    r"^\s*\*?\s*DB2:\s*Converted\s+"
    r"(?P<operation>OBTAIN\s+CALC|STORE|MODIFY|ERASE|DELETE|UPDATE|INSERT)"
    r"\s+(?:for\s+)?(?P<record>[A-Z0-9-]+)\.?\s*$",
    flags=re.IGNORECASE,
)

SKIPPED_FOR_PATTERN = re.compile(
    r"^\s*\*?\s*DB2:\s*"
    r"(?P<operation>SELECT|INSERT|UPDATE|DELETE|STORE|MODIFY|OBTAIN\s+CALC)"
    r"\s+conversion\s+skipped\s+for\s+(?P<record>[A-Z0-9-]+)\.?\s*$",
    flags=re.IGNORECASE,
)

REMOVED_OBTAIN_CALC_PATTERN = re.compile(
    r"^\s*\*?\s*DB2:\s*Removed\s+OBTAIN\s+CALC\s+SELECT\s+for\s+"
    r"(?P<record>[A-Z0-9-]+)\.?\s*$",
    flags=re.IGNORECASE,
)

SQLCODE_IF_PATTERN = re.compile(
    r"^\s*IF\s+SQLCODE\b",
    flags=re.IGNORECASE,
)

END_IF_PATTERN = re.compile(
    r"^\s*END-IF\.?\s*$",
    flags=re.IGNORECASE,
)

CONTINUE_PATTERN = re.compile(
    r"^\s*CONTINUE\.?\s*$",
    flags=re.IGNORECASE,
)

DB2_COMMENT_PATTERN = re.compile(
    r"^\s*\*?\s*DB2:",
    flags=re.IGNORECASE,
)