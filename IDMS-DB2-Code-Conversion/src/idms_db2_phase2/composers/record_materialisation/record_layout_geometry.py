# LOCATION: src/idms_db2_phase2/composers/record_materialisation/record_layout_geometry.py
# ACTION: CREATE NEW FILE
"""Fixed-format geometry for generated data description entries.

Pure arithmetic. No templates, no COBOL text, no plan knowledge - every
method takes strings and numbers and returns strings and numbers, so the
column rules can be reasoned about and tested in one place.

THE RULES THIS CLASS ENFORCES

  * levels 02-49 start in Area B, column 12 or later,
  * a body never reaches column 72,
  * a name is padded before its PICTURE, and the padding shrinks rather
    than letting the line overflow,
  * an entry carries EXACTLY ONE terminating period,
  * nesting indent is capped, so no depth can push a picture off the end.

CORRECTION 2 - nesting overflowed the body

    A fixed 4-space step put a level-11 entry at column 29 and pushed
    'PIC S9(3) COMP-3.' past column 72, so the emitter degraded to an
    unaligned fallback. The step is 2 spaces and the depth is capped.

CORRECTION 4 - double period on every group entry

    GROUP_ITEM_TEMPLATE ends in a period, ELEMENTARY_ITEM_TEMPLATE does
    not. Appending one unconditionally produced '06  VMBFAS..', which
    the compiler rejects. terminate() never assumes what a template did.
"""

from __future__ import annotations

from rules.record_materialisation_rules import (
    LAYOUT_BASE_INDENT,
    LAYOUT_BODY_WIDTH,
    LAYOUT_LEVEL_STEP,
    LAYOUT_MAX_INDENT_DEPTH,
    LAYOUT_MIN_NAME_GAP,
    LAYOUT_NAME_WIDTH,
    MAX_LEVEL,
    MIN_LEVEL,
)

PERIOD = "."


class RecordLayoutGeometry:
    """Column arithmetic for one data description entry."""

    BODY_WIDTH = LAYOUT_BODY_WIDTH
    PERIOD = PERIOD

    # ----------------------------------------------------------- indent
    @staticmethod
    def root(base_indent: str = "") -> str:
        """The indent of the field being expanded, or Area B."""
        return str(base_indent) if base_indent else LAYOUT_BASE_INDENT

    @staticmethod
    def indent_text(root: str, depth: int) -> str:
        """CORRECTION 2. Nesting indent is capped, never unbounded."""
        steps = max(0, min(int(depth), LAYOUT_MAX_INDENT_DEPTH))
        return str(root) + (LAYOUT_LEVEL_STEP * steps)

    # ------------------------------------------------------------ width
    @classmethod
    def name_width(
        cls,
        *,
        indent: str,
        level: str,
        name: str,
        picture: str,
    ) -> int:
        """Padding that keeps the entry inside columns 8-72.

        Shrinks the gap before the PICTURE rather than letting the line
        overflow, so alignment degrades gracefully and never truncates.
        """
        prefix = len(indent) + len(level) + 2
        available = cls.BODY_WIDTH - prefix - len(picture) - len(PERIOD)
        minimum = len(name) + LAYOUT_MIN_NAME_GAP

        if available < minimum:
            return minimum
        return max(minimum, min(LAYOUT_NAME_WIDTH, available))

    @classmethod
    def gap_before(cls, head: str, picture: str) -> int:
        """Spaces between a head fragment and its PICTURE. Never zero."""
        gap = cls.BODY_WIDTH - len(head) - len(picture) - len(PERIOD)
        return max(LAYOUT_MIN_NAME_GAP, gap)

    # ------------------------------------------------------ termination
    @staticmethod
    def terminate(body: str) -> str:
        """CORRECTION 4. Exactly one period, whatever the template did."""
        text = str(body or "").rstrip()
        if not text:
            return text
        return text.rstrip(PERIOD).rstrip() + PERIOD

    # -------------------------------------------------------------- cap
    @classmethod
    def cap(cls, body: str) -> str:
        """Last-resort guard against a body wider than columns 8-72."""
        text = str(body or "").rstrip()
        if len(text) <= cls.BODY_WIDTH:
            return text

        indent = text[: len(text) - len(text.lstrip(" "))]
        parts = text.strip().split()
        collapsed = indent + " ".join(parts)
        if len(collapsed) <= cls.BODY_WIDTH:
            return collapsed

        return " ".join(parts)[: cls.BODY_WIDTH]

    # ----------------------------------------------------------- levels
    @classmethod
    def shift(cls, level: str, amount: int) -> str:
        """Rebase a Sheet Mapping level under the record group."""
        try:
            return cls.clamp(int(str(level).strip()) + int(amount))
        except (TypeError, ValueError):
            return str(level)

    @staticmethod
    def clamp(value: int) -> str:
        bounded = max(MIN_LEVEL, min(MAX_LEVEL, int(value)))
        return f"{bounded:02d}"

    @staticmethod
    def depth(stack: list[str], level: str) -> int:
        """Nesting depth from the level stack, not a fixed table.

        Mutates `stack`, which is how a single left-to-right pass can
        track nesting without looking ahead.
        """
        while stack and stack[-1] >= level:
            stack.pop()
        found = len(stack)
        stack.append(level)
        return found


__all__ = ["PERIOD", "RecordLayoutGeometry"]