# LOCATION: patterns/sequence_patterns.py
# ACTION: REPLACE ENTIRE FILE

"""COBOL fixed-format sequence handling.

ROOT CAUSE CORRECTED IN THIS FILE
---------------------------------
The previous left-sequence pattern was:

    LEFT_SEQUENCE_PATTERN = re.compile(
        r"^\\s*(?P<seq>\\d{6})(?P<body>\\s+.*)$"
    )

The body group demanded WHITESPACE immediately after the six digits.

In fixed-format COBOL, position 7 is the INDICATOR AREA. It holds a space
on ordinary statement lines, but it legitimately holds:

    '*'  comment
    '/'  comment + page eject
    '-'  continuation
    'D'  debug line

On any such line the pattern did not match, so the left sequence number was
NEVER STRIPPED. Downstream consumers then saw the sequence number as COBOL
text:

    001690/                                                     00420000
        -> strip_sequence_numbers(...) returned "001690/"
        -> is_comment_or_blank("001690/") returned False
        -> ParagraphTerminatorCleanup appended a period
        -> "001690/."   <- not valid COBOL

That single defect also hid trailing IF ... WRITE ... END-IF blocks from
OutputWritePlacementCleanup, so a guarded output WRITE was never relocated
out of the child-row paragraph and fired once per fetched child row.

Stripping is now COLUMN-BASED, which is what the COBOL standard actually
specifies, with a regex fallback only for free-form text that carries no
fixed-format frame.

CONTRACT (unchanged for callers)
--------------------------------
strip_sequence_numbers(line) returns the line with columns 1-6 and 73-80
removed, KEEPING column 7 onwards. A comment line therefore still starts
with its '*' or '/' indicator, which is what is_comment_or_blank() relies
on.

This file must contain regex patterns and pure text helpers only.
No business rules, no layout constants, no program names.
"""

from __future__ import annotations

import re

# =====================================================================
# Fixed-format geometry
# =====================================================================
LEFT_SEQUENCE_START = 0
LEFT_SEQUENCE_END = 6
INDICATOR_INDEX = 6
BODY_START = 7
BODY_END = 72
RIGHT_SEQUENCE_START = 72
RIGHT_SEQUENCE_END = 80

MIN_ADDRESSABLE_LENGTH = 7

# Every indicator the COBOL standard permits in column 7.
VALID_INDICATORS = (" ", "*", "/", "D", "d", "-")
COMMENT_INDICATORS = ("*", "/")
DEBUG_INDICATORS = ("D", "d")
CONTINUATION_INDICATOR = "-"

# =====================================================================
# Patterns
# =====================================================================
# Left sequence followed by the indicator area. The body group now accepts
# ANY indicator character, not whitespace only. Kept for callers that
# import it directly.
LEFT_SEQUENCE_PATTERN = re.compile(
    r"^(?P<seq>\d{6})(?P<body>[ */\-Dd].*)?$",
)

# Trailing eight-digit right sequence on a free-form line.
RIGHT_SEQUENCE_PATTERN = re.compile(
    r"^(?P<body>.*?)\s+(?P<right>\d{8})\s*$",
)

# A body that is nothing but a leaked six-digit sequence number, with an
# optional indicator character and an optional period.
SEQUENCE_ARTIFACT_PATTERN = re.compile(
    r"^\s*\d{6}\s*[*/\-Dd]?\s*\.?\s*$",
)


# =====================================================================
# Helpers
# =====================================================================
def is_fixed_format_line(line: str) -> bool:
    """True when columns 1-6 are numeric and column 7 is a valid indicator.

    The right sequence is deliberately optional: hand-maintained members
    often leave it blank or truncate the line, and demanding it was what
    caused sequence numbers to be parsed as COBOL text.
    """
    text = str(line or "").rstrip("\n")

    if len(text) < MIN_ADDRESSABLE_LENGTH:
        return False

    if not text[LEFT_SEQUENCE_START:LEFT_SEQUENCE_END].isdigit():
        return False

    return text[INDICATOR_INDEX] in VALID_INDICATORS


def indicator_of(line: str) -> str:
    """Column 7 of a fixed-format line, or '' when there is none."""
    text = str(line or "").rstrip("\n")
    return text[INDICATOR_INDEX] if is_fixed_format_line(text) else ""


def is_comment_or_control(line: str) -> bool:
    """True for comment, page-eject and debug lines.

    Works on a RAW line, before any stripping, so a caller can classify
    correctly without relying on the stripped text starting with '*'.
    """
    text = str(line or "").rstrip("\n")

    if not text.strip():
        return False

    if is_fixed_format_line(text):
        return text[INDICATOR_INDEX] in COMMENT_INDICATORS + DEBUG_INDICATORS

    stripped = text.lstrip()
    return bool(stripped) and stripped[0] in COMMENT_INDICATORS


def is_sequence_artifact(line: str) -> bool:
    """True when the stripped body is only a leaked sequence number."""
    body = strip_sequence_numbers(line).strip()
    if not body:
        return False
    return bool(SEQUENCE_ARTIFACT_PATTERN.match(body))


def strip_left_sequence(line: str) -> str:
    """Remove columns 1-6, keeping the indicator and the body."""
    text = str(line or "").rstrip("\n")

    if is_fixed_format_line(text):
        return text[LEFT_SEQUENCE_END:]

    match = LEFT_SEQUENCE_PATTERN.match(text)
    if match:
        return match.group("body") or ""

    return text


def strip_right_sequence(line: str) -> str:
    """Remove columns 73-80."""
    text = str(line or "").rstrip("\n")

    if is_fixed_format_line(text) and len(text) > RIGHT_SEQUENCE_START:
        return text[:RIGHT_SEQUENCE_START]

    match = RIGHT_SEQUENCE_PATTERN.match(text)
    if match:
        return match.group("body")

    return text


def strip_sequence_numbers(line: str) -> str:
    """Remove columns 1-6 and 73-80, KEEPING column 7 onwards.

    A comment line therefore still begins with its '*' or '/' indicator,
    preserving the contract every existing caller depends on.
    """
    text = str(line or "").rstrip("\n")

    if is_fixed_format_line(text):
        padded = text.ljust(RIGHT_SEQUENCE_END)
        return padded[INDICATOR_INDEX:RIGHT_SEQUENCE_START].rstrip()

    return strip_right_sequence(strip_left_sequence(text)).rstrip()


def logical_body(line: str) -> str:
    """Columns 8-72 only, stripped. Indicator excluded."""
    text = str(line or "").rstrip("\n")

    if is_fixed_format_line(text):
        padded = text.ljust(RIGHT_SEQUENCE_END)
        return padded[BODY_START:BODY_END].strip()

    return strip_sequence_numbers(text).strip()


__all__ = [
    "LEFT_SEQUENCE_PATTERN",
    "RIGHT_SEQUENCE_PATTERN",
    "SEQUENCE_ARTIFACT_PATTERN",
    "VALID_INDICATORS",
    "COMMENT_INDICATORS",
    "DEBUG_INDICATORS",
    "CONTINUATION_INDICATOR",
    "is_fixed_format_line",
    "indicator_of",
    "is_comment_or_control",
    "is_sequence_artifact",
    "strip_left_sequence",
    "strip_right_sequence",
    "strip_sequence_numbers",
    "logical_body",
]