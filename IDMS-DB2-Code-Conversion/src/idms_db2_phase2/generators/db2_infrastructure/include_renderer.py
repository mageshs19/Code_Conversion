# LOCATION: src/idms_db2_phase2/generators/db2_infrastructure/include_renderer.py
# ACTION: CREATE NEW FILE

"""Single source of truth for EXEC SQL INCLUDE emission and detection.

Every component that emits or looks for an include routes through here,
so the shape, the indent and the duplicate test cannot drift apart
again.

The detection side is deliberately SHAPE-AGNOSTIC: it recognises an
include whether it was written on one line or across a three-line block.
Duplicate detection that saw only one shape is exactly what let
DZBFARTV be injected twice.
"""

from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.db2_include_patterns import (
    END_EXEC_PATTERN,
    EXEC_SQL_OPEN_PATTERN,
    INCLUDE_BODY_PATTERN,
    INCLUDE_NAME_PATTERN,
    INCLUDE_SINGLE_PATTERN,
)
from rules.db2_include_rules import (
    IND_INCLUDE,
    IND_INCLUDE_BODY,
    INCLUDE_BLOCK_BODY_TEMPLATE,
    INCLUDE_BLOCK_CLOSE,
    INCLUDE_BLOCK_OPEN,
    INCLUDE_SINGLE_LINE,
    INCLUDE_SINGLE_TEMPLATE,
    INFRASTRUCTURE_INCLUDES,
)


class IncludeRenderer:
    """Renders include statements and finds the ones already present."""

    def __init__(self, line_utils=None) -> None:
        self.line_utils = line_utils

    # =================================================================
    # Rendering
    # =================================================================
    def render(self, name: str) -> list[str]:
        """One include, in the site's canonical shape and indent."""
        clean = self.normalize(name)
        if not clean:
            return []

        if INCLUDE_SINGLE_LINE:
            return [
                IND_INCLUDE + INCLUDE_SINGLE_TEMPLATE.format(name=clean)
            ]

        return [
            IND_INCLUDE + INCLUDE_BLOCK_OPEN,
            IND_INCLUDE_BODY
            + INCLUDE_BLOCK_BODY_TEMPLATE.format(name=clean),
            IND_INCLUDE + INCLUDE_BLOCK_CLOSE,
        ]

    def render_all(self, names: list[str]) -> list[str]:
        """Render each distinct include once, order preserved."""
        out: list[str] = []
        seen: set[str] = set()

        for name in names or []:
            clean = self.normalize(name)
            if not clean or clean in seen:
                continue
            seen.add(clean)
            out.extend(self.render(clean))

        return out

    # =================================================================
    # Detection
    # =================================================================
    def existing(self, lines: list[str]) -> set[str]:
        """Every include already present, whichever shape carries it."""
        found: set[str] = set()

        for line in lines or []:
            logical = self._logical(line)
            if not logical:
                continue

            match = INCLUDE_SINGLE_PATTERN.match(logical)
            if match:
                found.add(self.normalize(match.group("name")))
                continue

            match = INCLUDE_BODY_PATTERN.match(logical)
            if match:
                found.add(self.normalize(match.group("name")))

        found.discard("")
        return found

    def counts(self, lines: list[str]) -> dict[str, int]:
        """How many times each include appears. Duplicates show as > 1."""
        totals: dict[str, int] = {}
        inside_block = False

        for line in lines or []:
            logical = self._logical(line)
            if not logical:
                continue

            single = INCLUDE_SINGLE_PATTERN.match(logical)
            if single:
                name = self.normalize(single.group("name"))
                totals[name] = totals.get(name, 0) + 1
                continue

            if EXEC_SQL_OPEN_PATTERN.match(logical):
                inside_block = True
                continue

            if END_EXEC_PATTERN.match(logical):
                inside_block = False
                continue

            if not inside_block:
                continue

            body = INCLUDE_BODY_PATTERN.match(logical)
            if body:
                name = self.normalize(body.group("name"))
                totals[name] = totals.get(name, 0) + 1

        totals.pop("", None)
        return totals

    def missing(
        self,
        lines: list[str],
        required: list[str],
    ) -> list[str]:
        """Required includes not already present, order preserved."""
        present = self.existing(lines)
        out: list[str] = []
        seen: set[str] = set()

        for name in required or []:
            clean = self.normalize(name)
            if not clean or clean in present or clean in seen:
                continue
            seen.add(clean)
            out.append(clean)

        return out

    # =================================================================
    # Classification
    # =================================================================
    @staticmethod
    def is_infrastructure(name: str) -> bool:
        """SQLCA, SQLERRWS, SQLERROR and GEN are not DCLGEN tables."""
        return NameNormalizer.normalize(name).upper() in INFRASTRUCTURE_INCLUDES

    # =================================================================
    # Helpers
    # =================================================================
    @staticmethod
    def normalize(name: str) -> str:
        return NameNormalizer.normalize(str(name or "")).upper()

    def _logical(self, line: str) -> str:
        """Strip the sequence area, whatever helper the caller supplied."""
        if self.line_utils is not None:
            getter = getattr(self.line_utils, "logical", None)
            if callable(getter):
                return str(getter(line) or "").strip().upper()

        from patterns.sequence_patterns import strip_sequence_numbers

        return strip_sequence_numbers(str(line or "")).strip().upper()