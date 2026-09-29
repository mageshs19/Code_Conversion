# LOCATION: zowe/zowe_patterns.py
# ACTION: REPLACE ENTIRE FILE
"""Regex patterns used only by the zowe package.

Regex only. No business rules, file paths, program names, DB2 table names,
DCLGEN names, copybook names, or host variables belong here.
"""

from __future__ import annotations

import re

# ---- Dataset and member validation ----

# A configured value must be a library, not a member path.
MEMBER_PATH_PATTERN = re.compile(r"[()]")

# A valid dataset name: dot-separated qualifiers, 1-8 characters each.
DATASET_NAME_PATTERN = re.compile(
    r"^[A-Z$#@][A-Z0-9$#@-]{0,7}(\.[A-Z$#@][A-Z0-9$#@-]{0,7})*$",
    flags=re.IGNORECASE,
)

# Characters that are not legal in a local file stem.
UNSAFE_FILENAME_CHAR_PATTERN = re.compile(r"[^A-Za-z0-9_-]")

# ---- Selective fetch: members the source program references ----

COPY_MEMBER_PATTERN = re.compile(
    r"^\s*COPY\s+(?P<member>[A-Z0-9][A-Z0-9$#@-]*)\s*\.?",
    flags=re.IGNORECASE | re.MULTILINE,
)

COPY_IDMS_LR_PATTERN = re.compile(
    r"^\s*COPY\s+IDMS\s+LR\s+(?P<lr>[A-Z0-9][A-Z0-9-]*)\b",
    flags=re.IGNORECASE | re.MULTILINE,
)

INCLUDE_DCLGEN_PATTERN = re.compile(
    r"\bINCLUDE\s+(?P<member>[A-Z][A-Z0-9_]*)\b",
    flags=re.IGNORECASE,
)

# ---- Output file naming ----

# Output file stem carries a timestamp: VMDZ7201_29-09-2026_143000.cbl
OUTPUT_STEM_PATTERN = re.compile(
    r"^(?P<stem>[A-Z0-9$#@-]+?)(?:_\d{2}-\d{2}-\d{4}_\d{6})?$",
    flags=re.IGNORECASE,
)

# ---- .env parsing and value resolution ----

# A .env line: KEY=VALUE, ignoring blanks and comments.
DOTENV_LINE_PATTERN = re.compile(
    r"^\s*(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>.*?)\s*$"
)

# An explicit reference to another key, braced or bare.
ENV_REFERENCE_PATTERN = re.compile(
    r"\$\{(?P<key>[A-Za-z_][A-Za-z0-9_]*)\}|\$(?P<bare>[A-Za-z_][A-Za-z0-9_]*)"
)

# A value that is nothing but a ZOWE_ key name. Almost always a typo:
# the operator meant to reference it, not to use it as a literal.
BARE_ENV_KEY_PATTERN = re.compile(r"^ZOWE_[A-Z0-9_]+$")

# LOCATION: zowe/zowe_patterns.py
# ACTION: APPEND at the end of the file

# A plain copybook COPY. "COPY IDMS ..." is excluded deliberately.
PLAIN_COPY_PATTERN = re.compile(
    r"^\s*COPY\s+(?!IDMS\b)(?P<member>[A-Z0-9][A-Z0-9$#@-]*)\s*\.?",
    flags=re.IGNORECASE | re.MULTILINE,
)

# COPY IDMS RECORD <record-name>.
COPY_IDMS_RECORD_PATTERN = re.compile(
    r"^\s*COPY\s+IDMS\s+RECORD\s+(?P<record>[A-Z0-9][A-Z0-9-]*)\s*\.?",
    flags=re.IGNORECASE | re.MULTILINE,
)

# SCHEMA SECTION.  DB <subschema> WITHIN <schema>.
DB_WITHIN_PATTERN = re.compile(
    r"^\s*DB\s+(?P<subschema>[A-Z0-9][A-Z0-9-]*)\s+WITHIN\s+"
    r"(?P<schema>[A-Z0-9][A-Z0-9-]*)\s*\.?",
    flags=re.IGNORECASE | re.MULTILINE,
)

# IDMS navigation verbs naming a record.
IDMS_VERB_RECORD_PATTERN = re.compile(
    r"\b(?:OBTAIN|FIND|STORE|MODIFY|ERASE)\s+"
    r"(?:FIRST|NEXT|LAST|PRIOR|CALC|ANY|EACH|CURRENT|OWNER)?\s*"
    r"(?P<record>[A-Z][A-Z0-9-]{2,})\b",
    flags=re.IGNORECASE,
)

# Source program id shape: VM 7 BD 200
SOURCE_PROGRAM_ID_PATTERN = re.compile(
    r"^(?P<app>[A-Z]{2})(?P<digit>[0-9])(?P<suffix>[A-Z]{2})(?P<tail>[0-9A-Z]+)$",
    flags=re.IGNORECASE,
)