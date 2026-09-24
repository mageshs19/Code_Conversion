# LOCATION: patterns/lrf_patterns.py
# ACTION: CREATE NEW FILE
"""Regex for the IDMS subschema Logical Record Facility (LRF) source."""

from __future__ import annotations

import re

SUBSCHEMA_HEADER_PATTERN = re.compile(
    r"^\s*ADD\s+SUBSCHEMA\s+NAME\s+IS\s+(?P<subschema>[A-Z0-9-]+)"
    r"\s+OF\s+SCHEMA\s+NAME\s+IS\s+(?P<schema>[A-Z0-9-]+)",
    re.IGNORECASE,
)

LOGICAL_RECORD_PATTERN = re.compile(
    r"^\s*ADD\s+LOGICAL\s+RECORD\s+(?P<lr>[A-Z0-9-]+)",
    re.IGNORECASE,
)

ELEMENTS_ARE_PATTERN = re.compile(r"^\s*ELEMENTS\s+ARE\s*$", re.IGNORECASE)
COMMENTS_PATTERN = re.compile(r"^\s*COMMENTS\s*$", re.IGNORECASE)
QUOTED_TEXT_PATTERN = re.compile(r"'(?P<text>[^']*)'")

PATH_GROUP_PATTERN = re.compile(
    r"^\s*ADD\s+PATH-GROUP\s+(?P<verb>[A-Z]+)\s+(?P<lr>[A-Z0-9-]+)",
    re.IGNORECASE,
)

SELECT_KEYWORD_PATTERN = re.compile(
    r"^\s*SELECT\s+FOR\s+KEYWORD\s+(?P<keyword>[A-Z0-9-]+)",
    re.IGNORECASE,
)

FIND_OBTAIN_PATTERN = re.compile(
    r"^\s*(?P<verb>FIND|OBTAIN)\s+(?P<scope>CURRENT|EACH|FIRST|NEXT|OWNER)?"
    r"\s*(?P<record>[A-Z0-9-]+)"
    r"(?:\s+WITHIN\s+(?P<within>[A-Z0-9-]+))?",
    re.IGNORECASE,
)

ERASE_PATTERN = re.compile(r"^\s*ERASE\s+(?P<record>[A-Z0-9-]+)", re.IGNORECASE)

IF_SET_EMPTY_PATTERN = re.compile(
    r"^\s*IF\s+(?P<set_name>[A-Z0-9-]+)\s+IS\s+(?P<negate>NOT\s+)?EMPTY",
    re.IGNORECASE,
)

WHERE_PATTERN = re.compile(r"^\s*WHERE\s+(?P<clause>.+?)\s*$", re.IGNORECASE)

ON_STATUS_PATTERN = re.compile(
    r"^\s*ON\s+(?P<status>\d{4})\s+(?P<action>.+?)\s*$",
    re.IGNORECASE,
)

ELEMENT_NAME_PATTERN = re.compile(r"^\s*(?P<record>[A-Z][A-Z0-9-]*)\s*$")

# The program-side hook: COPY IDMS LR VMBTL03-R01.
COPY_IDMS_LR_PATTERN = re.compile(
    r"^\s*COPY\s+IDMS\s+LR\s+(?P<lr>[A-Z0-9-]+)\s*\.",
    re.IGNORECASE,
)

# LR-qualified field reference: KY-SIFORM OF VMBSIAS OF LR
LR_QUALIFIED_FIELD_PATTERN = re.compile(
    r"(?P<field>[A-Z0-9-]+)\s+OF\s+(?P<record>[A-Z0-9-]+)\s+OF\s+LR",
    re.IGNORECASE,
)