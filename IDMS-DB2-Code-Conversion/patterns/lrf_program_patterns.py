# LOCATION: patterns/lrf_program_patterns.py
# ACTION: CREATE NEW FILE
"""Regex for LRF syntax appearing in the COBOL PROGRAM (not the subschema).

patterns/lrf_patterns.py owns the SUBSCHEMA source regex.
This module owns what the program itself writes.
"""

from __future__ import annotations

import re

# OBTAIN FIRST VMBTL03-R01 WHERE SWEEP-VMBFAS.
# OBTAIN NEXT  VMBTL03-R01 WHERE VMBFAS-BY-VMBSIAS.
LR_OBTAIN_WHERE_PATTERN = re.compile(
    r"^\s*OBTAIN\s+(?:KEEP\s+)?(?P<mode>FIRST|NEXT|EACH|LAST|PRIOR)\s+"
    r"(?P<lr>[A-Z][A-Z0-9-]*)\s+"
    r"WHERE\s+(?P<keyword>[A-Z][A-Z0-9-]*)\s*\.?\s*$",
    flags=re.IGNORECASE,
)

# ERASE VMBTL03-R01 WHERE ERASE-VMBSIAS.
LR_ERASE_WHERE_PATTERN = re.compile(
    r"^\s*ERASE\s+(?P<lr>[A-Z][A-Z0-9-]*)\s+"
    r"WHERE\s+(?P<keyword>[A-Z][A-Z0-9-]*)\s*\.?\s*$",
    flags=re.IGNORECASE,
)

# MODIFY / STORE logical record forms.
LR_MODIFY_WHERE_PATTERN = re.compile(
    r"^\s*(?P<verb>MODIFY|STORE)\s+(?P<lr>[A-Z][A-Z0-9-]*)\s+"
    r"WHERE\s+(?P<keyword>[A-Z][A-Z0-9-]*)\s*\.?\s*$",
    flags=re.IGNORECASE,
)

# LR-STATUS = 'VMBFAS-EOA'   /   LR-STATUS NOT = 'VMBFAS-EOA'
LR_STATUS_CONDITION_PATTERN = re.compile(
    r"\bLR-STATUS\b\s*(?P<operator>NOT\s*=|=|NOT\s+EQUAL\s+TO|EQUAL\s+TO)\s*"
    r"'(?P<literal>[^']*)'",
    flags=re.IGNORECASE,
)

# Any bare LR-STATUS reference (MOVE, DISPLAY, IF ... etc.)
LR_STATUS_TOKEN_PATTERN = re.compile(
    r"\bLR-STATUS\b",
    flags=re.IGNORECASE,
)

# KY-SIFORM OF VMBSIAS OF LR  ->  KY-SIFORM OF VMBSIAS
OF_LR_SUFFIX_PATTERN = re.compile(
    r"(?P<head>\b[A-Z][A-Z0-9-]*\s+OF\s+[A-Z][A-Z0-9-]*)\s+OF\s+LR\b",
    flags=re.IGNORECASE,
)

# A trailing bare "OF LR" with no record qualifier.
BARE_OF_LR_PATTERN = re.compile(
    r"\s+OF\s+LR\b",
    flags=re.IGNORECASE,
)

# COPY IDMS SUBSCHEMA-LR-CTRL.
COPY_SUBSCHEMA_LR_CTRL_PATTERN = re.compile(
    r"^\s*COPY\s+IDMS\s+SUBSCHEMA-LR-CTRL\s*\.",
    flags=re.IGNORECASE,
)