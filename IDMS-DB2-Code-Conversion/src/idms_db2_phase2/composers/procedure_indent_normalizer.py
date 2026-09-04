"""
Procedure Division indentation normalizer.

Runs late (before final resequence) to give PROCEDURE DIVISION executable
statements a consistent, DEPTH-AWARE Area-B indentation. Fixes irregular
indents produced by different generators (SQL MOVEs, EXEC SQL, timestamp
MOVEs, etc.) and indents IF / EVALUATE / PERFORM..END-PERFORM bodies
progressively to match the manual COBOL standard.

Safe scope:
  - Only PROCEDURE DIVISION.
  - Only executable statement lines (space indicator in column 7).
  - Never touches comments ('*' / '/'), debug lines ('D'), Area-A
    paragraph/section headers, or the DATA/other divisions.
  - Preserves the 80-column frame: rewrites only columns 8-72 body indent;
    left seq (1-6) and right seq (73-80) untouched.
  - EXEC SQL...END-EXEC blocks keep the flat SQL body indent (not depth).

Indentation model:
  - Base Area-B executable statement -> 4 spaces (physical column 12).
  - Each nested IF / EVALUATE / PERFORM..END-PERFORM level -> +3 spaces.
  - ELSE / WHEN / END-IF / END-EVALUATE / END-PERFORM dedent one level.
  - EXEC SQL / END-EXEC             -> current block indent.
  - SQL body lines inside EXEC SQL  -> +3 under the EXEC SQL line.
  - Paragraph headers (Area A)      -> unchanged, reset depth to 0.
"""

from __future__ import annotations

import re

BASE_INDENT = 4        # spaces -> physical column 12 (Area B base)
INDENT_STEP = 3        # spaces per nesting level
SQL_BODY_STEP = 3      # extra indent for SQL body lines inside EXEC SQL

DIVISION_PROCEDURE = re.compile(
    r"^\s*(?:\d{6})?\s*PROCEDURE\s+DIVISION\b",
    flags=re.IGNORECASE,
)
PARAGRAPH_HEADER = re.compile(
    r"^[A-Z0-9][A-Z0-9-]*\.\s*$",
    flags=re.IGNORECASE,
)
SECTION_HEADER = re.compile(
    r"^[A-Z0-9-]+\s+SECTION\.\s*$",
    flags=re.IGNORECASE,
)
EXEC_SQL_START = re.compile(r"^EXEC\s+SQL\b", flags=re.IGNORECASE)
EXEC_SQL_END = re.compile(r"^END-EXEC\.?\s*$", flags=re.IGNORECASE)

# Block openers (increase depth AFTER the line is placed).
BLOCK_OPEN = re.compile(r"^(IF|EVALUATE)\b", flags=re.IGNORECASE)
PERFORM_INLINE_OPEN = re.compile(
    r"^PERFORM\b(?!.*\bEND-PERFORM\b).*$", flags=re.IGNORECASE
)
# Block closers (decrease depth; the closer itself sits at the outer level).
BLOCK_CLOSE = re.compile(
    r"^(END-IF|END-EVALUATE|END-PERFORM)\b", flags=re.IGNORECASE
)
# Mid-block keywords: sit one level out, body stays inside.
BLOCK_MID = re.compile(r"^(ELSE|WHEN)\b", flags=re.IGNORECASE)

# Area-A executable-ish tokens that must stay at column 8 (indent 0).
AREA_A_WORDS = (
    "IDENTIFICATION",
    "ENVIRONMENT",
    "DATA",
    "PROCEDURE",
)


class ProcedureIndentNormalizer:

    def __init__(self) -> None:
        self.messages: list[str] = []

    def compose(self, text: str) -> str:
        if not text:
            return ""

        lines = text.replace("\r\n", "\n").split("\n")
        output: list[str] = []
        in_procedure = False
        in_exec_sql = False
        changed = False
        depth = 0                 # IF / EVALUATE / PERFORM nesting depth
        perform_depth_stack: list[int] = []  # tracks END-PERFORM openers

        for line in lines:
            if not self._is_fixed_line(line):
                output.append(line)
                if DIVISION_PROCEDURE.search(line):
                    in_procedure = True
                continue

            left = line[:6]
            indicator = line[6]
            body = line[7:72]
            right = line[72:80]
            logical = body.strip()

            # Enter PROCEDURE DIVISION.
            if DIVISION_PROCEDURE.search(logical):
                in_procedure = True
                depth = 0
                output.append(line)
                continue

            if not in_procedure:
                output.append(line)
                continue

            # Never touch comments / debug / page lines.
            if indicator in ("*", "/", "D", "d"):
                output.append(line)
                continue

            if not logical:
                output.append(line)
                continue

            upper = logical.upper()

            # Area-A structural lines stay put and reset depth.
            if PARAGRAPH_HEADER.match(logical) or SECTION_HEADER.match(logical):
                depth = 0
                in_exec_sql = False
                output.append(line)
                continue
            if upper.startswith(AREA_A_WORDS):
                depth = 0
                output.append(line)
                continue

            # ---- EXEC SQL block handling (flat SQL body, not depth-based) ----
            if EXEC_SQL_START.match(logical):
                indent = " " * (BASE_INDENT + depth * INDENT_STEP)
                new_body = indent + logical
                in_exec_sql = True
                output.append(self._rebuild(left, new_body, right))
                changed = True
                continue

            if EXEC_SQL_END.match(logical):
                indent = " " * (BASE_INDENT + depth * INDENT_STEP)
                new_body = indent + logical
                in_exec_sql = False
                output.append(self._rebuild(left, new_body, right))
                changed = True
                continue

            if in_exec_sql:
                indent = " " * (BASE_INDENT + depth * INDENT_STEP + SQL_BODY_STEP)
                new_body = indent + logical
                output.append(self._rebuild(left, new_body, right))
                changed = True
                continue

            # ---- Depth-aware Area-B indentation ----
            line_depth = depth
            if BLOCK_CLOSE.match(logical) or BLOCK_MID.match(logical):
                line_depth = max(0, depth - 1)

            indent = " " * (BASE_INDENT + line_depth * INDENT_STEP)
            new_body = indent + logical
            output.append(self._rebuild(left, new_body, right))
            changed = True

            # ---- Adjust depth AFTER placing the line ----
            if BLOCK_OPEN.match(logical):
                depth += 1
            elif PERFORM_INLINE_OPEN.match(logical) and " UNTIL " not in (" " + upper + " "):
                # PERFORM ... (inline, no END-PERFORM, not an inline UNTIL loop)
                # Only treat as an opener if the source uses END-PERFORM style.
                # Conservative: do NOT open depth for simple PERFORM name.
                pass
            elif upper.startswith("PERFORM") and "END-PERFORM" not in upper \
                    and self._is_perform_block_opener(upper):
                depth += 1
                perform_depth_stack.append(depth)
            elif BLOCK_CLOSE.match(logical):
                depth = max(0, depth - 1)
                if upper.startswith("END-PERFORM") and perform_depth_stack:
                    perform_depth_stack.pop()

        if changed:
            self.messages.append(
                "Procedure indent normalizer: normalized depth-aware Area-B "
                "executable statement indentation."
            )

        return "\n".join(output).rstrip() + "\n"

    @staticmethod
    def _is_perform_block_opener(upper: str) -> bool:
        """A PERFORM that starts an inline (END-PERFORM) block.

        Only 'PERFORM' or 'PERFORM ... UNTIL' with NO paragraph name and NO
        trailing period opens an inline block. A plain 'PERFORM paragraph.'
        does not. Conservative to avoid over-indentation.
        """
        text = upper.strip().rstrip(".")
        # inline block form: "PERFORM UNTIL ..." or bare "PERFORM"
        if text == "PERFORM":
            return True
        if text.startswith("PERFORM UNTIL"):
            return True
        if text.startswith("PERFORM VARYING"):
            return True
        return False

    @staticmethod
    def _is_fixed_line(line: str) -> bool:
        text = str(line or "").rstrip("\n")
        return (
            len(text) >= 80
            and text[:6].isdigit()
            and text[72:80].isdigit()
        )

    @staticmethod
    def _rebuild(left: str, new_body: str, right: str) -> str:
        body_area = new_body[:65].ljust(65)
        return f"{left[:6].zfill(6)}{' '}{body_area[:65]}{right[:8]}"