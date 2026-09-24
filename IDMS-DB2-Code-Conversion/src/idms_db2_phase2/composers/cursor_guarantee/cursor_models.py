# LOCATION: src/idms_db2_phase2/composers/cursor_guarantee/cursor_models.py
# ACTION: CREATE NEW FILE

"""Regex, value objects and the diagnostic log. The passive parts.

WHY THE REGEX LIVES HERE
------------------------
The project rule puts regex in patterns/. This package is a documented
exception, and the exception is earned: the shared pattern module was
reachable by two paths, so the first module to request a name while it
was still executing failed with

    ImportError: cannot import name 'CONTINUE_PATTERN' from partially
    initialized module 'patterns.cursor_close_guarantee_patterns'

The defect was latent for exactly as long as the composer was never
constructed. This module imports NOTHING from the project, so no import
order can break it.

Nothing here makes a decision. No project, paragraph, record, table,
cursor or host variable name is hardcoded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rules.cursor_close_guarantee_rules import (
    CURSOR_CLOSE_GUARANTEE_MESSAGES,
    OPERATION_CLOSE,
    OPERATION_FETCH,
    OPERATION_OPEN,
    REQUIRED_OPERATIONS,
)

COMMENT_INDICATORS = ("*", "/")
UNTIL_KEYWORD = "UNTIL"

# Generated cursor paragraph name, e.g. 710-OPEN-DZBFASC1.
PARAGRAPH_NAME_TEMPLATE = "{number:03d}-{operation}-{cursor}"

# =====================================================================
# Regex
#
# A COBOL paragraph name may begin with a DIGIT: every generated cursor
# paragraph is numbered. A pattern requiring a leading letter makes the
# whole generated block invisible, which is how an earlier guard pass
# commented out 60 working lines.
# =====================================================================
_NAME = r"[A-Z0-9][A-Z0-9-]*"

PARAGRAPH_HEADER_PATTERN = re.compile(
    rf"^(?P<name>{_NAME})\s*\.\s*$",
    flags=re.IGNORECASE,
)

SECTION_HEADER_PATTERN = re.compile(
    rf"^(?P<name>{_NAME})\s+SECTION\s*\.\s*$",
    flags=re.IGNORECASE,
)

# 710-OPEN-DZBFASC1.  /  720-FETCH-DZBFASC1.  /  730-CLOSE-DZBFASC1.
CURSOR_PARAGRAPH_HEADER_PATTERN = re.compile(
    rf"^(?P<number>\d{{3,6}})-"
    rf"(?P<operation>OPEN|FETCH|CLOSE)-"
    rf"(?P<cursor>{_NAME})\s*\.\s*$",
    flags=re.IGNORECASE,
)

# PERFORM 720-FETCH-DZBFASC1.                     -> tail ""
# PERFORM 720-FETCH-DZBFASC1 UNTIL DZBFASC1-EOC.  -> tail " UNTIL ..."
#
# The tail is captured rather than matched, so CursorPerform.has_until
# needs no second pattern.
PERFORM_CURSOR_PARAGRAPH_PATTERN = re.compile(
    rf"^PERFORM\s+(?P<number>\d{{3,6}})-"
    rf"(?P<operation>OPEN|FETCH|CLOSE)-"
    rf"(?P<cursor>{_NAME})"
    rf"(?P<tail>.*)$",
    flags=re.IGNORECASE,
)

PERFORM_PARAGRAPH_PATTERN = re.compile(
    rf"^PERFORM\s+(?P<paragraph>{_NAME})\s*(?P<terminator>\.?)\s*$",
    flags=re.IGNORECASE,
)

PERFORM_INLINE_WITH_UNTIL_PATTERN = re.compile(
    rf"^PERFORM\s+(?P<paragraph>{_NAME})\s+UNTIL\s+"
    rf"(?P<condition>.+?)\s*(?P<terminator>\.?)\s*$",
    flags=re.IGNORECASE,
)

PERFORM_SPAN_PATTERN = re.compile(
    rf"^PERFORM\s+(?P<paragraph>{_NAME})\s+(?:THRU|THROUGH)\s+"
    rf"(?P<through>{_NAME})\s*(?P<terminator>\.?)\s*$",
    flags=re.IGNORECASE,
)

PERFORM_SPAN_WITH_UNTIL_PATTERN = re.compile(
    rf"^PERFORM\s+(?P<paragraph>{_NAME})\s+(?:THRU|THROUGH)\s+"
    rf"(?P<through>{_NAME})\s+UNTIL\s+"
    rf"(?P<condition>.+?)\s*(?P<terminator>\.?)\s*$",
    flags=re.IGNORECASE,
)

UNTIL_ONLY_PATTERN = re.compile(
    r"^UNTIL\s+(?P<condition>.+?)\s*(?P<terminator>\.?)\s*$",
    flags=re.IGNORECASE,
)

WHEN_ZERO_PATTERN = re.compile(
    r"^WHEN\s+(?:ZERO|ZEROES|ZEROS|0)\s*$",
    flags=re.IGNORECASE,
)

CONTINUE_PATTERN = re.compile(
    r"^CONTINUE\s*\.?\s*$",
    flags=re.IGNORECASE,
)


# =====================================================================
# Value objects
# =====================================================================
@dataclass
class ParagraphHeader:
    """One paragraph header line."""

    index: int = -1
    name: str = ""


@dataclass
class CursorParagraphSet:
    """The OPEN / FETCH / CLOSE paragraph names of one cursor."""

    cursor: str = ""
    names: dict = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        return all(operation in self.names for operation in REQUIRED_OPERATIONS)

    @property
    def open_name(self) -> str:
        return self.names.get(OPERATION_OPEN, "")

    @property
    def fetch_name(self) -> str:
        return self.names.get(OPERATION_FETCH, "")

    @property
    def close_name(self) -> str:
        return self.names.get(OPERATION_CLOSE, "")


@dataclass
class CursorPerform:
    """One PERFORM of a generated cursor paragraph."""

    index: int = -1
    operation: str = ""
    paragraph: str = ""
    tail: str = ""

    @property
    def has_until(self) -> bool:
        return UNTIL_KEYWORD in str(self.tail or "").upper()


@dataclass
class LoopShape:
    """A business driving loop found in the generated flow."""

    perform_index: int = -1
    until_index: int = -1
    end_index: int = -1
    condition: str = ""
    terminated: bool = False

    @property
    def has_condition(self) -> bool:
        return bool(str(self.condition or "").strip())


class MessageLog:
    """Ordered diagnostics for one conversion run.

    Every helper writes into ONE instance, so the composer exposes a
    single `messages` list and no two helpers can drift out of order.

    An unknown key or a template/value mismatch must never LOSE the
    diagnostic: an unreported repair is the exact failure this pass
    exists to end.
    """

    def __init__(self) -> None:
        self.messages: list[str] = []

    def reset(self) -> None:
        self.messages = []

    def log(self, key: str, **values) -> None:
        template = CURSOR_CLOSE_GUARANTEE_MESSAGES.get(key, "")

        if not template:
            self.messages.append(f"Cursor close guarantee: {key} {values}")
            return

        try:
            self.messages.append(template.format(**values))
        except (IndexError, KeyError):
            self.messages.append(f"{template} [{key}: {values}]")


__all__ = [
    "COMMENT_INDICATORS",
    "UNTIL_KEYWORD",
    "PARAGRAPH_NAME_TEMPLATE",
    "PARAGRAPH_HEADER_PATTERN",
    "SECTION_HEADER_PATTERN",
    "CURSOR_PARAGRAPH_HEADER_PATTERN",
    "PERFORM_CURSOR_PARAGRAPH_PATTERN",
    "PERFORM_PARAGRAPH_PATTERN",
    "PERFORM_INLINE_WITH_UNTIL_PATTERN",
    "PERFORM_SPAN_PATTERN",
    "PERFORM_SPAN_WITH_UNTIL_PATTERN",
    "UNTIL_ONLY_PATTERN",
    "WHEN_ZERO_PATTERN",
    "CONTINUE_PATTERN",
    "ParagraphHeader",
    "CursorParagraphSet",
    "CursorPerform",
    "LoopShape",
    "MessageLog",
]