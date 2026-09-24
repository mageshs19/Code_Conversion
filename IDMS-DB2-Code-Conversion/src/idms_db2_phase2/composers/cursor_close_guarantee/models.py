# LOCATION: src/idms_db2_phase2/composers/cursor_close_guarantee/models.py
# ACTION: CREATE NEW FILE

"""Value objects for the cursor close-guarantee pass.

Data only. No logic, no regex, no constants beyond the shape of the
records themselves.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rules.cursor_close_guarantee_rules import (
    OPERATION_CLOSE,
    OPERATION_FETCH,
    OPERATION_OPEN,
    REQUIRED_OPERATIONS,
)

UNTIL_KEYWORD = "UNTIL"


@dataclass
class ParagraphHeader:
    """One paragraph header line in the generated program."""

    index: int = -1
    name: str = ""


@dataclass
class CursorParagraphSet:
    """The generated OPEN / FETCH / CLOSE paragraph names of one cursor."""

    cursor: str = ""
    names: dict = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        return all(
            operation in self.names for operation in REQUIRED_OPERATIONS
        )

    @property
    def open_name(self) -> str:
        return self.names.get(OPERATION_OPEN, "")

    @property
    def fetch_name(self) -> str:
        return self.names.get(OPERATION_FETCH, "")

    @property
    def close_name(self) -> str:
        return self.names.get(OPERATION_CLOSE, "")

    def remember(self, operation: str, name: str) -> None:
        """First occurrence wins; a duplicate header is never honoured."""
        self.names.setdefault(operation, name)


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


__all__ = [
    "UNTIL_KEYWORD",
    "ParagraphHeader",
    "CursorParagraphSet",
    "CursorPerform",
    "LoopShape",
]