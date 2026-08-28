"""
Procedure Division indentation normalizer.

Runs late (before final resequence) to give PROCEDURE DIVISION executable
statements a consistent Area-B indentation, fixing irregular 2-space or
6-space indents produced by different generators (SQL MOVEs, EXEC SQL,
timestamp MOVEs, etc.).

Safe scope:
  - Only PROCEDURE DIVISION.
  - Only executable statement lines (space indicator in column 7).
  - Never touches comments ('*' / '/'), debug lines ('D'), Area-A
    paragraph/section headers, or the DATA/other divisions.
  - Preserves the 80-column frame: rewrites only columns 8-72 body indent;
    left seq (1-6) and right seq (73-80) untouched.

Indentation model:
  - Area-B executable statements    -> 4 spaces (physical column 12).
  - EXEC SQL / END-EXEC             -> 4 spaces.
  - SQL body lines inside EXEC SQL  -> 7 spaces (nested under EXEC SQL).
  - Paragraph headers (Area A)      -> unchanged.
"""

from __future__ import annotations

import re

AREA_B_INDENT = "    "          # 4 spaces  -> column 12
SQL_BODY_INDENT = "       "     # 7 spaces  -> nested SQL body

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

        for line in lines:
            if not self._is_fixed_line(line):
                output.append(line)
                # still track division on non-fixed lines defensively
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

            # Area-A structural lines stay put.
            if PARAGRAPH_HEADER.match(logical) or SECTION_HEADER.match(logical):
                output.append(line)
                continue
            if upper.startswith(AREA_A_WORDS):
                output.append(line)
                continue

            # Track EXEC SQL blocks for nested SQL body indent.
            if EXEC_SQL_START.match(logical):
                new_body = AREA_B_INDENT + logical
                in_exec_sql = True
                output.append(self._rebuild(left, new_body, right))
                changed = True
                continue

            if EXEC_SQL_END.match(logical):
                new_body = AREA_B_INDENT + logical
                in_exec_sql = False
                output.append(self._rebuild(left, new_body, right))
                changed = True
                continue

            if in_exec_sql:
                new_body = SQL_BODY_INDENT + logical
                output.append(self._rebuild(left, new_body, right))
                changed = True
                continue

            # Regular Area-B executable statement -> 4-space indent.
            new_body = AREA_B_INDENT + logical
            output.append(self._rebuild(left, new_body, right))
            changed = True

        if changed:
            self.messages.append(
                "Procedure indent normalizer: normalized Area-B "
                "executable statement indentation."
            )

        return "\n".join(output).rstrip() + "\n"

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