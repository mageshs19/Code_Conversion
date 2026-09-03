from __future__ import annotations

import re


RIGHT_SEQUENCE_PATTERN = re.compile(
    r"^(?P<body>.*?)(?:\s+(?P<right>\d{8}))\s*$",
    flags=re.IGNORECASE,
)


LEFT_SEQUENCE_PATTERN = re.compile(
    r"^(?P<left>\s*\d{6}\s+)(?P<body>.*)$",
    flags=re.IGNORECASE,
)


RIGHT_SEQUENCE_WITH_SPACES_PATTERN = re.compile(
    r"^(?P<body>.*?)(?P<spaces>\s+)(?P<right>\d{8})\s*$",
    flags=re.IGNORECASE,
)


IDMS_DECLARATIVE_PATTERNS = [
    re.compile(
        r"^IDMS-CONTROL\s+SECTION\.?$",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^PROTOCOL\b.*$",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^IDMS-RECORDS\s+WITHIN\s+WORKING-STORAGE\s+SECTION\.?$",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^SCHEMA\s+SECTION\.?$",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^DB\s+[A-Z0-9-]+\s+WITHIN\s+[A-Z0-9-]+\.?$",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^COPY\s+IDMS\b.*$",
        flags=re.IGNORECASE,
    ),
]


IDMS_EXECUTABLE_PATTERNS = [
    re.compile(
        r"^BIND\b.*$",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^FIND\s+CURRENT\b.*$",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^FINISH\.?$",
        flags=re.IGNORECASE,
    ),
]


IDMS_ABORT_PARAGRAPH_PATTERN = re.compile(
    r"^IDMS-ABORT\.?$",
    flags=re.IGNORECASE,
)


EXIT_LINE_PATTERN = re.compile(
    r"^EXIT\.?$",
    flags=re.IGNORECASE,
)


FINISH_STATEMENT_PATTERN = re.compile(
    r"^FINISH\.?$",
    flags=re.IGNORECASE,
)


BIND_STATEMENT_PATTERN = re.compile(
    r"^BIND\b",
    flags=re.IGNORECASE,
)


FIND_CURRENT_STATEMENT_PATTERN = re.compile(
    r"^FIND\s+CURRENT\b",
    flags=re.IGNORECASE,
)