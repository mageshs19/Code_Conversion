# LOCATION: src/idms_db2_phase2/services/cobol_area_alignment_reflow.py
# ACTION: REPLACE ENTIRE FILE

"""COBOL Area B safe two-line reflow helper.

This module only handles long-line reflow using an existing continuation
line. It does not decide Procedure Division state or SQL state.

WHAT A CONTINUATION LINE IS
---------------------------
A fixed-format COBOL statement may continue onto the next line with NO
continuation indicator, provided the break falls on a space between two
complete words. The '-' indicator in column 7 is required only when a
word or literal is split mid-token.

This helper therefore breaks on word boundaries ONLY, and never emits a
continuation indicator.

CORRECTION - combined-budget truncation
---------------------------------------
The previous version joined the statement with its continuation fragment
and re-split the pair on EVERY call, against a fixed combined budget,
slicing the overflow off the tail:

    MOVE AM-CNSTK-479BEFF OF DCLDZBEFFTV
    TO UIT-AM-                                <- UIT-AM-CN-STOCK

Every affected pair measured exactly 60 combined body characters, with
the remainder discarded, producing undefined data names.

A two-line statement is correct COBOL. Re-splitting it was unnecessary
work, and truncating the result was destructive.

This version:

- PRESERVES the existing break. The pair is re-indented in place; the
  words are not moved.
- REBALANCES at a word boundary only when the FIRST line alone no longer
  fits columns 8-72 at its new indent.
- REFUSES - returns [] so the caller leaves both lines exactly as they
  were - whenever the pair cannot be represented.
- NEVER truncates, never splits a data name, never collapses the
  statement onto one line.
- Delegates all column arithmetic to FixedFormatLineService. No private
  copy of the geometry is kept here.

Contract preserved: try_reflow_with_next_line returns either an empty
list, or EXACTLY TWO lines replacing the two it was given. It never adds
or removes physical lines.
"""

from __future__ import annotations

from idms_db2_phase2.services.cobol_area_alignment_classifier import (
    CobolAreaAlignmentClassifier,
)
from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from rules.final_feedback_fix_rules import AREA_B_CONTINUATION_BODY_INDENT

# Statement-starting keywords. A next line beginning with one of these is
# a NEW statement, not a continuation fragment, and must never be joined
# to the line above.
STATEMENT_KEYWORDS = (
    "ACCEPT", "ADD", "ALTER", "CALL", "CANCEL", "CLOSE", "COMPUTE",
    "CONTINUE", "DELETE", "DISPLAY", "DIVIDE", "ELSE", "EVALUATE",
    "EXEC", "EXIT", "GO", "GOBACK", "IF", "INITIALIZE", "INSPECT",
    "MERGE", "MOVE", "MULTIPLY", "OPEN", "PERFORM", "READ", "RELEASE",
    "RETURN", "REWRITE", "SEARCH", "SET", "SORT", "START", "STOP",
    "STRING", "SUBTRACT", "UNSTRING", "WHEN", "WRITE",
)

DIVISION_TOKENS = ("DIVISION", "SECTION")


class CobolAreaAlignmentReflow:
    """Re-indents a two-line statement without ever truncating it."""

    def __init__(
        self,
        *,
        fixed_format: FixedFormatLineService,
        classifier: CobolAreaAlignmentClassifier,
    ) -> None:
        self.fixed_format = fixed_format
        self.classifier = classifier

    # =================================================================
    # Public entry point
    # =================================================================
    def try_reflow_with_next_line(
        self,
        *,
        current_line: str,
        next_line: str,
        first_indent: str,
    ) -> list[str]:
        """Re-indent a statement that spans the current and next lines.

        Returns:
            []                  leave both lines untouched
            [first, second]     replacements for the two input lines
        """
        if not current_line or not next_line:
            return []

        if not self.fixed_format.is_fixed_line(current_line):
            return []

        if not self.fixed_format.is_fixed_line(next_line):
            return []

        if not self._is_continuation_fragment(next_line):
            return []

        current_logical = self.fixed_format.logical(current_line)
        next_logical = self.fixed_format.logical(next_line)

        if not current_logical or not next_logical:
            return []

        indent = str(first_indent or "")
        continuation = indent + AREA_B_CONTINUATION_BODY_INDENT

        first_body = indent + current_logical
        second_body = continuation + next_logical

        # --- Case 1: the author's break still works -----------------
        #
        # Preferred path. The words stay exactly where the generator or
        # the programmer put them; only the indent changes.
        if self.fixed_format.body_fits(first_body) and self.fixed_format.body_fits(
            second_body
        ):
            return self._render(current_line, next_line, first_body, second_body)

        # --- Case 2: rebalance at a word boundary -------------------
        #
        # The first line no longer fits at its new indent. Move whole
        # words - never part of a word - onto the continuation line.
        joined = f"{current_logical} {next_logical}".strip()
        bodies = self.fixed_format.wrap_body_lines(
            indent + joined,
            continuation_indent=continuation,
            max_lines=2,
        )

        if len(bodies) != 2:
            # Cannot be represented in two lines. Refuse rather than cut.
            return []

        return self._render(current_line, next_line, bodies[0], bodies[1])

    # =================================================================
    # Rendering
    # =================================================================
    def _render(
        self,
        current_line: str,
        next_line: str,
        first_body: str,
        second_body: str,
    ) -> list[str]:
        """Rebuild both lines, or refuse if either will not assemble."""
        first_left, first_indicator, _b1, first_right = self.fixed_format.split(
            current_line
        )
        next_left, next_indicator, _b2, next_right = self.fixed_format.split(
            next_line
        )

        first = self.fixed_format.build_or_none(
            first_left,
            first_indicator or " ",
            first_body,
            first_right,
        )
        second = self.fixed_format.build_or_none(
            next_left,
            next_indicator or " ",
            second_body,
            next_right,
        )

        if first is None or second is None:
            return []

        return [first, second]

    # =================================================================
    # Guards
    # =================================================================
    def _is_continuation_fragment(self, line: str) -> bool:
        """True when `line` is the tail of the statement above it.

        A paragraph header, section or division header, scope terminator,
        sentence terminator, comment, page eject or a NEW statement is
        not a continuation. Joining any of those to the line above would
        corrupt the program.
        """
        if self.fixed_format.is_comment_or_control_line(line):
            return False

        if self.fixed_format.is_sequence_artifact(line):
            return False

        logical = self.fixed_format.logical(line)
        if not logical:
            return False

        upper = logical.upper()
        words = upper.split()

        # Lone sentence terminator.
        if upper == ".":
            return False

        # Paragraph header: a single word ending in a period.
        if len(words) == 1 and upper.endswith("."):
            return False

        # Scope terminator.
        if upper.startswith("END-"):
            return False

        # Division or section header.
        if any(token in words for token in DIVISION_TOKENS):
            return False

        # A new statement.
        if words and words[0].rstrip(".") in STATEMENT_KEYWORDS:
            return False

        return True