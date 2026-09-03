"""
Fixed-format COBOL regex patterns.
These patterns are used by fixed-format composers and helpers.
Keep regex definitions here instead of defining them inside composer classes.
"""
import re
LEFT_SEQUENCE_PATTERN = re.compile(
r"^\s*(?P<left>\d{6})(?P<rest>.*)$",
flags=re.IGNORECASE,
)
RIGHT_SEQUENCE_PATTERN = re.compile(
r"^(?P<body>.*?)(?P<right>\d{8})\s*$",
flags=re.IGNORECASE,
)
SEQUENCE_ONLY_PATTERN = re.compile(
r"^\s*(\d{6}|\d{8})\s*$",
flags=re.IGNORECASE,
)
DIVISION_PATTERN = re.compile(
r"^(IDENTIFICATION|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION\b.*\.?$",
flags=re.IGNORECASE,
)
SECTION_PATTERN = re.compile(
r"^[A-Z0-9-]+\s+SECTION\.?$",
flags=re.IGNORECASE,
)
PARAGRAPH_PATTERN = re.compile(
r"^[A-Z0-9][A-Z0-9-]*\.?$",
flags=re.IGNORECASE,
)
AREA_A_PREFIX_PATTERN = re.compile(
(
r"^("
r"PROGRAM-ID\.|"
r"AUTHOR\.|"
r"INSTALLATION\.|"
r"DATE-WRITTEN\.|"
r"DATE-COMPILED\.|"
r"SECURITY\.|"
r"FD\s+|"
r"SD\s+|"
r"01\s+|"
r"66\s+|"
r"77\s+"
r")"
),
flags=re.IGNORECASE,
)
DATA_LEVEL_PATTERN = re.compile(
r"^(0[1-9]|[1-4][0-9]|66|77|88)\s+",
flags=re.IGNORECASE,
)
EXEC_SQL_START_PATTERN = re.compile(
r"^EXEC\s+SQL\b",
flags=re.IGNORECASE,
)
EXEC_SQL_END_PATTERN = re.compile(
r"^END-EXEC\.?$",
flags=re.IGNORECASE,
)
BOOLEAN_OPERATOR_END_PATTERN = re.compile(
r"\b(AND|OR)\s*$",
flags=re.IGNORECASE,
)
IF_BOOLEAN_SPLIT_PATTERN = re.compile(
r"(\s+AND\s+|\s+OR\s+)",
flags=re.IGNORECASE,
)
MOVE_STATEMENT_PATTERN = re.compile(
r"^MOVE\s+(?P<src>.+?)\s+TO\s+(?P<tgt>.+?\.?)$",
flags=re.IGNORECASE,
)
DEBUG_LINE_PATTERN = re.compile(
r"^[Dd]\s+",
flags=re.IGNORECASE,
)

# --- Fixed-format line parser sequence patterns (appended) ---

# A true left sequence number: exactly six digits in columns 1-6 followed by
# whitespace and a body.
TRUE_LEFT_SEQUENCE_PATTERN = re.compile(
    r"^(?P<left>\d{6})(?P<body>\s+.*)$",
    flags=re.IGNORECASE,
)

# Right sequence number separated from the body by spaces.
RIGHT_SEQUENCE_WITH_SPACES_PATTERN = re.compile(
    r"^(?P<body>.*?)(?P<spaces>\s+)(?P<right>\d{8})\s*$",
    flags=re.IGNORECASE,
)

# Right sequence number accidentally attached to the body (no spaces).
TRAILING_TIGHT_RIGHT_SEQUENCE_PATTERN = re.compile(
    r"^(?P<body>.*\S)(?P<right>\d{8})\s*$",
    flags=re.IGNORECASE,
)

# A single COBOL identifier token (used to detect body endings).
COBOL_IDENTIFIER_TOKEN_PATTERN = re.compile(
    r"[A-Z][A-Z0-9-]*",
    flags=re.IGNORECASE,
)