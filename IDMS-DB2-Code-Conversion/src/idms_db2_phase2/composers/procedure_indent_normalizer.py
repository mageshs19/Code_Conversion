# LOCATION: src/idms_db2_phase2/composers/procedure_indent_normalizer.py
# ACTION: REPLACE ENTIRE FILE

"""Procedure Division indentation normalizer.

Runs late (before final resequence) to give PROCEDURE DIVISION executable
statements a consistent, DEPTH-AWARE Area-B indentation. Fixes irregular
indents produced by different generators (SQL MOVES, EXEC SQL, timestamp
MOVES, etc.) and indents IF / EVALUATE / PERFORM .. END-PERFORM bodies
progressively to match the manual COBOL standard.

Safe scope
----------
- Only PROCEDURE DIVISION.
- Only executable statement lines (space indicator in column 7).
- Never touches comments ('*' / '/'), debug lines ('D'), continuation
  lines ('-'), Area-A paragraph/section headers, or the DATA and other
  divisions.
- Preserves the 80-column frame: rewrites only columns 8-72 body indent;
  left seq (1-6) and right seq (73-80) untouched.
- EXEC SQL ... END-EXEC blocks keep the flat SQL body indent, not depth.

CORRECTION - silent truncation
------------------------------
This class previously carried a PRIVATE copy of the fixed-format geometry
that had drifted from the shared service:

    @staticmethod
    def _is_fixed_line(line):
        return (len(text) >= 80 and text[:6].isdigit()
                and text[72:80].isdigit())

    @staticmethod
    def _rebuild(left, new_body, right):
        body_area = new_body[:65].ljust(65)      # <-- silent truncation
        return f"{left[:6].zfill(6)}{' '}{body_area[:65]}{right[:8]}"

Two defects followed.

1. _is_fixed_line demanded a full 80 columns AND a numeric right
   sequence, so a short page-eject line such as '001690/' was misparsed
   and its sequence number could reach the COBOL body.

2. _rebuild truncated any body past column 72 without telling anyone.
   Because this normalizer is the LAST content pass in the pipeline, it
   is how

       MOVE NR-IDGOOD-479EVEF OF DCLDZEVEFTV    TO WS-NR-ID-GOOD

   was written out as

       MOVE NR-IDGOOD-479EVEF OF DCLDZEVEFTV    TO WS-NR-ID-GO

   producing an undefined data name that the compiler rejects.

Geometry is now delegated entirely to FixedFormatLineService. A re-indent
that no longer fits is WRAPPED onto a continuation line; if even that is
impossible the original line is kept unchanged. A cosmetic pass must
never destroy a statement.

TEMPORARY INSTRUMENTATION
-------------------------
A four-line IF condition reached the generated file merged into two
truncated lines. This pass processes ONE line at a time and has no join
path, so the merge must happen upstream. DUMP_INTERMEDIATE writes the
text this pass receives and the text it returns, which settles the
question in one run. Set it to False, or delete the three marked blocks,
once the culprit is fixed.

Clean Architecture
------------------
- Constants live in rules/procedure_indent_rules.py.
- Regex lives in patterns/procedure_indent_patterns.py.
- No program, paragraph, record, table, cursor or host variable name is
  hardcoded.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path  # TEMP DEBUG

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from patterns.procedure_indent_patterns import (
    ELSE_PATTERN,
    END_EXEC_PATTERN,
    EVALUATE_START_PATTERN,
    EXEC_SQL_START_PATTERN,
    IF_START_PATTERN,
    INLINE_PERFORM_PATTERN,
    LONE_PERIOD_PATTERN,
    OTHER_DIVISION_PATTERN,
    PARAGRAPH_HEADER_PATTERN,
    PROCEDURE_DIVISION_PATTERN,
    SCOPE_TERMINATOR_PATTERN,
    SCOPED_OPENER_PATTERN,
    SECTION_HEADER_PATTERN,
    WHEN_PATTERN,
)
from rules.procedure_indent_rules import (
    AREA_A_INDENT,
    AREA_B_INDENT,
    BLOCK_KIND_EVALUATE,
    BLOCK_KIND_IF,
    BLOCK_KIND_OTHER,
    BLOCK_KIND_PERFORM,
    BLOCK_KIND_SQL,
    ENFORCE_PROCEDURE_INDENT,
    LONE_PERIOD_INDENT,
    MAX_NESTING_DEPTH,
    NEST_STEP,
    NON_PARAGRAPH_SINGLE_WORDS,
    PROCEDURE_INDENT_MESSAGES,
    SCOPE_TERMINATORS,
    SQL_BODY_OFFSET,
    WHEN_BODY_OFFSET,
    WHEN_OFFSET,
)

# TEMP DEBUG - set False or delete the marked blocks once the upstream
# merge is fixed.
DUMP_INTERMEDIATE = True
DUMP_IN = "debug_indent_in.txt"
DUMP_OUT = "debug_indent_out.txt"


@dataclass
class _Frame:
    """One open block on the indentation stack."""

    kind: str
    own_indent: int

    @property
    def body_indent(self) -> int:
        if self.kind == BLOCK_KIND_EVALUATE:
            return self.own_indent + WHEN_BODY_OFFSET
        if self.kind == BLOCK_KIND_SQL:
            return self.own_indent + SQL_BODY_OFFSET
        return self.own_indent + NEST_STEP

    @property
    def when_indent(self) -> int:
        return self.own_indent + WHEN_OFFSET


class ProcedureIndentNormalizer:
    """Depth-aware Area-B re-indentation for the PROCEDURE DIVISION."""

    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.fixed_format = fixed_format or FixedFormatLineService()
        self.messages: list[str] = []

    # =================================================================
    # Public entry point
    # =================================================================
    def compose(self, text: str) -> str:
        self.messages = []

        self._dump(DUMP_IN, text)  # TEMP DEBUG

        if not text or not ENFORCE_PROCEDURE_INDENT:
            return str(text or "")

        lines = (
            str(text)
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .split("\n")
        )

        output: list[str] = []
        stack: list[_Frame] = []
        in_procedure = False
        normalized = 0
        wrapped = 0

        for number, line in enumerate(lines, start=1):
            # --- lines this pass must never touch --------------------
            if self._is_untouchable(line):
                output.append(line)
                continue

            logical = self.fixed_format.logical(line)
            if not logical:
                output.append(line)
                continue

            upper = logical.upper()

            # --- division boundaries ---------------------------------
            if PROCEDURE_DIVISION_PATTERN.match(upper):
                in_procedure = True
                stack = []
                output.append(line)
                continue

            if OTHER_DIVISION_PATTERN.match(upper):
                in_procedure = False
                stack = []
                output.append(line)
                continue

            if not in_procedure:
                output.append(line)
                continue

            # --- Area A headers reset the stack ----------------------
            if self._is_area_a_header(upper):
                stack = []
                rendered = self._render(line, AREA_A_INDENT, logical)
                output.extend(rendered)
                if len(rendered) > 1:
                    wrapped += len(rendered) - 1
                if rendered[0] != line:
                    normalized += 1
                continue

            # --- depth guard -----------------------------------------
            if len(stack) > MAX_NESTING_DEPTH:
                self.messages.append(
                    PROCEDURE_INDENT_MESSAGES["skipped_depth"].format(
                        limit=MAX_NESTING_DEPTH,
                        line=number,
                    )
                )
                output.append(line)
                continue

            indent, stack = self._resolve(upper, stack)

            rendered = self._render(line, indent, logical)
            output.extend(rendered)

            if len(rendered) > 1:
                wrapped += len(rendered) - 1
            if rendered[0] != line:
                normalized += 1

        if normalized:
            self.messages.append(
                PROCEDURE_INDENT_MESSAGES["normalized"].format(
                    count=normalized
                )
            )
        if wrapped:
            self.messages.append(
                PROCEDURE_INDENT_MESSAGES["wrapped"].format(count=wrapped)
            )

        result = "\n".join(output).rstrip() + "\n"

        self._dump(DUMP_OUT, result)  # TEMP DEBUG

        return result

    # =================================================================
    # Temporary instrumentation
    # =================================================================
    @staticmethod
    def _dump(name: str, text: str) -> None:  # TEMP DEBUG
        """Write one pipeline snapshot. Never raises, never blocks."""
        if not DUMP_INTERMEDIATE:
            return

        try:
            Path(name).write_text(str(text or ""), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    # =================================================================
    # Indent resolution
    # =================================================================
    def _resolve(
        self,
        upper: str,
        stack: list[_Frame],
    ) -> tuple[int, list[_Frame]]:
        """Return the body indent for this line and the updated stack."""
        current = stack[-1].body_indent if stack else AREA_B_INDENT

        # --- END-EXEC: close the SQL frame -------------------------
        if END_EXEC_PATTERN.match(upper):
            frame = self._pop(stack, BLOCK_KIND_SQL)
            return (frame.own_indent if frame else current), stack

        # --- inside EXEC SQL: flat body, no depth -------------------
        if stack and stack[-1].kind == BLOCK_KIND_SQL:
            return stack[-1].body_indent, stack

        # --- scope terminators --------------------------------------
        terminator = SCOPE_TERMINATOR_PATTERN.match(upper)
        if terminator:
            token = terminator.group("token").upper()
            kind = SCOPE_TERMINATORS.get(token, BLOCK_KIND_OTHER)
            frame = self._pop(stack, kind)
            return (frame.own_indent if frame else AREA_B_INDENT), stack

        # --- lone period closes the paragraph sentence --------------
        if LONE_PERIOD_PATTERN.match(upper):
            stack.clear()
            return LONE_PERIOD_INDENT, stack

        # --- ELSE aligns with its IF --------------------------------
        if ELSE_PATTERN.match(upper):
            frame = self._peek(stack, BLOCK_KIND_IF)
            return (frame.own_indent if frame else AREA_B_INDENT), stack

        # --- WHEN aligns against its EVALUATE -----------------------
        if WHEN_PATTERN.match(upper):
            frame = self._peek(stack, BLOCK_KIND_EVALUATE)
            return (
                frame.when_indent if frame else AREA_B_INDENT + WHEN_OFFSET
            ), stack

        # --- openers render at the current indent, then push --------
        if EXEC_SQL_START_PATTERN.match(upper):
            stack.append(_Frame(BLOCK_KIND_SQL, current))
            return current, stack

        if EVALUATE_START_PATTERN.match(upper):
            stack.append(_Frame(BLOCK_KIND_EVALUATE, current))
            return current, stack

        if IF_START_PATTERN.match(upper):
            if not self._is_self_closing(upper):
                stack.append(_Frame(BLOCK_KIND_IF, current))
            return current, stack

        if INLINE_PERFORM_PATTERN.match(upper):
            if not self._is_self_closing(upper):
                stack.append(_Frame(BLOCK_KIND_PERFORM, current))
            return current, stack

        if SCOPED_OPENER_PATTERN.match(upper):
            if self._opens_scope(upper):
                stack.append(_Frame(BLOCK_KIND_OTHER, current))
            return current, stack

        # --- ordinary statement -------------------------------------
        return current, stack

    # =================================================================
    # Stack helpers
    # =================================================================
    @staticmethod
    def _pop(stack: list[_Frame], kind: str) -> _Frame | None:
        """Pop the nearest frame of `kind`, tolerating a mismatch."""
        for index in range(len(stack) - 1, -1, -1):
            if stack[index].kind == kind:
                frame = stack[index]
                del stack[index:]
                return frame

        if stack:
            return stack.pop()

        return None

    @staticmethod
    def _peek(stack: list[_Frame], kind: str) -> _Frame | None:
        for index in range(len(stack) - 1, -1, -1):
            if stack[index].kind == kind:
                return stack[index]
        return None

    # =================================================================
    # Classification
    # =================================================================
    def _is_untouchable(self, line: str) -> bool:
        """Comment, page-eject, debug, continuation or blank."""
        if not str(line or "").strip():
            return True

        if self.fixed_format.is_comment_or_control_line(line):
            return True

        if self.fixed_format.is_continuation_line(line):
            return True

        return self.fixed_format.is_sequence_artifact(line)

    @staticmethod
    def _is_area_a_header(upper: str) -> bool:
        if SECTION_HEADER_PATTERN.match(upper):
            return True

        match = PARAGRAPH_HEADER_PATTERN.match(upper)
        if not match:
            return False

        name = match.group("name").upper()
        return name not in NON_PARAGRAPH_SINGLE_WORDS

    @staticmethod
    def _is_self_closing(upper: str) -> bool:
        """A one-line block that already carries its own terminator.

        Example: IF X = 1 MOVE A TO B END-IF
        """
        text = upper.rstrip(".")
        return text.endswith("END-IF") or text.endswith("END-PERFORM")

    @staticmethod
    def _opens_scope(upper: str) -> bool:
        """A READ / SEARCH / STRING that is not already terminated."""
        text = upper.rstrip(".")
        if text.endswith(("END-READ", "END-SEARCH", "END-STRING",
                          "END-UNSTRING")):
            return False
        return not upper.endswith(".")

    # =================================================================
    # Rendering
    # =================================================================
    def _render(
        self,
        line: str,
        indent: int,
        logical: str,
    ) -> list[str]:
        """Re-indent one statement, wrapping instead of truncating.

        Returns the ORIGINAL line unchanged when the new body cannot be
        represented at all, so a cosmetic pass can never destroy code.
        """
        new_body = (" " * max(indent, 0)) + logical

        if new_body == self.fixed_format.body(line).rstrip():
            return [line]

        if self.fixed_format.body_fits(new_body):
            return [self.fixed_format.replace_body(line, new_body)]

        rendered = self.fixed_format.replace_body_wrapped(line, new_body)
        return rendered if rendered else [line]


__all__ = ["ProcedureIndentNormalizer"]