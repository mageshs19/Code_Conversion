"""CHK-06 Area A and Area B alignment."""

from __future__ import annotations

import re

from code_review.engine.check_base import MINOR, Check
from code_review.standards import cobol_standards as std

DIVISION = re.compile(r"^(?P<name>[A-Z]+)\s+DIVISION\b")
SECTION = re.compile(r"^(?P<name>[A-Z0-9][A-Z0-9-]*)\s+SECTION\s*\.?$")
PARAGRAPH = re.compile(r"^(?P<name>[A-Z0-9][A-Z0-9-]*)\.$")
LEVEL = re.compile(r"^(?P<level>\d{2})\s+(?P<name>[A-Z0-9][A-Z0-9-]*)")
PROCEDURE_DIVISION = re.compile(r"^PROCEDURE\s+DIVISION\b")

SQL_START = re.compile(rf"^{re.escape(std.SQL_BLOCK_START)}\b")
SQL_END = re.compile(rf"\b{re.escape(std.SQL_BLOCK_END)}\b")
STATUS_START = re.compile(rf"^{re.escape(std.SQL_STATUS_BLOCK_START)}\b")
STATUS_END = re.compile(rf"\b{re.escape(std.SQL_STATUS_BLOCK_END)}\b")


class AreaAlignmentCheck(Check):
    CHECK_ID = "CHK-06"
    TITLE = "Area A and Area B alignment"
    SEVERITY = MINOR
    ORDER = 60

    def relevant(self, ctx, view) -> bool:
        return any(line.is_fixed for line in view.code)

    def not_relevant_reason(self) -> str:
        return "No fixed-format lines to measure indentation against."

    def review(self, ctx, view, record):
        lines = [line for line in view.code if line.is_fixed]
        generated = self._generated_sql_lines(lines)
        generated_numbers = {line.number for line in generated}

        area_a = {
            line.number for line in lines
            if line.indent <= std.AREA_A_MAX_INDENT
        }
        area_b = {
            line.number for line in lines
            if line.indent >= std.AREA_B_MIN_INDENT
        }

        # ---- 01 division headers ------------------------------------
        divisions = [
            line for line in lines
            if DIVISION.match(line.logical)
            and DIVISION.match(line.logical).group("name") in std.DIVISION_NAMES
        ]
        if not divisions:
            record.skip(
                "01",
                f"Division headers start in Area A "
                f"(cols {std.AREA_A_FIRST_COLUMN}-{std.AREA_A_LAST_COLUMN})",
                "No division header found.",
            )
        else:
            record.expect_none(
                "01",
                f"Division headers start in Area A "
                f"(cols {std.AREA_A_FIRST_COLUMN}-{std.AREA_A_LAST_COLUMN})",
                [l for l in divisions if l.number not in area_a],
            )

        # ---- 02 section headers -------------------------------------
        sections = [line for line in lines if SECTION.match(line.logical)]
        if not sections:
            record.skip(
                "02", "Section headers start in Area A",
                "No section header found.",
            )
        else:
            record.expect_none(
                "02", "Section headers start in Area A",
                [l for l in sections if l.number not in area_a],
            )

        # ---- 03 paragraph headers -----------------------------------
        paragraphs = self._paragraph_headers(lines, generated_numbers)
        if not paragraphs:
            record.skip(
                "03", "Paragraph headers start in Area A",
                "No paragraph header found.",
            )
        else:
            record.expect_none(
                "03", "Paragraph headers start in Area A",
                [l for l in paragraphs if l.number not in area_a],
            )

        # ---- 04 level 01 and 77 -------------------------------------
        top_levels = [
            line for line in lines
            if LEVEL.match(line.logical)
            and LEVEL.match(line.logical).group("level")
            in std.AREA_A_LEVEL_NUMBERS
        ]
        if not top_levels:
            record.skip(
                "04",
                f"Level {' and '.join(std.AREA_A_LEVEL_NUMBERS)} items "
                f"start in Area A",
                "No level 01 or 77 item found.",
            )
        else:
            record.expect_none(
                "04",
                f"Level {' and '.join(std.AREA_A_LEVEL_NUMBERS)} items "
                f"start in Area A",
                [l for l in top_levels if l.number not in area_a],
            )

        # ---- 05 subordinate levels ----------------------------------
        sub_levels = [
            line for line in lines
            if LEVEL.match(line.logical)
            and LEVEL.match(line.logical).group("level")
            in std.AREA_B_LEVEL_NUMBERS
        ]
        if not sub_levels:
            record.skip(
                "05",
                f"Subordinate level items start in Area B "
                f"(col {std.AREA_B_FIRST_COLUMN} onward)",
                "No subordinate level item found.",
            )
        else:
            record.expect_none(
                "05",
                f"Subordinate level items start in Area B "
                f"(col {std.AREA_B_FIRST_COLUMN} onward)",
                [l for l in sub_levels if l.number not in area_b],
            )

        # ---- 06 procedure statements --------------------------------
        #
        # Generated DB2 block lines are excluded here and measured by
        # criterion 07 instead, so decision D-8 has exactly one gate.
        if not std.ENFORCE_AREA_B_STATEMENT_INDENT:
            record.skip(
                "06", "Procedure statements start in Area B",
                "Not enforced by the site standard.",
            )
        else:
            statements = self._procedure_statements(lines, generated_numbers)
            if not statements:
                record.skip(
                    "06", "Procedure statements start in Area B",
                    "No hand-written PROCEDURE DIVISION statement found.",
                )
            else:
                record.expect_none(
                    "06", "Procedure statements start in Area B",
                    [l for l in statements if l.number not in area_b],
                )

        # ---- 07 generated DB2 blocks --------------------------------
        if not std.ENFORCE_AREA_B_SQL_INDENT:
            record.skip(
                "07", "Generated DB2 blocks sit in Area B",
                "Generated DB2 block indentation not yet agreed "
                "(decision open).",
            )
        elif not generated:
            record.skip(
                "07", "Generated DB2 blocks sit in Area B",
                "Program contains no generated DB2 block.",
            )
        else:
            record.expect_none(
                "07", "Generated DB2 blocks sit in Area B",
                [
                    l for l in generated
                    if l.indent < std.AREA_B_SQL_MIN_INDENT
                ],
            )

        # ---- 08 continuation lines ----------------------------------
        continuations = [
            line for line in view.lines
            if line.is_fixed
            and line.indicator == std.CONTINUATION_INDICATOR
        ]
        if not continuations:
            record.skip(
                "08", "Continuation lines sit in Area B",
                "No continuation line found.",
            )
        else:
            record.expect_none(
                "08", "Continuation lines sit in Area B",
                [l for l in continuations if l.indent < std.AREA_B_MIN_INDENT],
            )

    # ---- helpers ----------------------------------------------------
    @staticmethod
    def _paragraph_headers(lines, generated: set[int]) -> list:
        """Real paragraph headers only.

        A bare word followed by a period is a paragraph header only when it
        is not a COBOL verb or scope terminator, is not a section header,
        and is not inside a generated DB2 block.
        """
        out = []
        for line in lines:
            if line.number in generated:
                continue
            if SECTION.match(line.logical):
                continue
            match = PARAGRAPH.match(line.logical)
            if not match:
                continue
            if match.group("name") in std.NON_PARAGRAPH_WORDS:
                continue
            out.append(line)
        return out

    @staticmethod
    def _procedure_statements(lines, generated: set[int]) -> list:
        """Hand-written executable lines after PROCEDURE DIVISION."""
        out = []
        started = False
        for line in lines:
            if PROCEDURE_DIVISION.match(line.logical):
                started = True
                continue
            if not started:
                continue
            if line.number in generated:
                continue
            if DIVISION.match(line.logical) or SECTION.match(line.logical):
                continue
            match = PARAGRAPH.match(line.logical)
            if match and match.group("name") not in std.NON_PARAGRAPH_WORDS:
                continue
            out.append(line)
        return out

    @staticmethod
    def _generated_sql_lines(lines) -> list:
        """Every line of a generated DB2 block, terminators included.

        Covers two block shapes emitted by the converter:

            EXEC SQL ... END-EXEC.
            EVALUATE SQLCODE ... END-EVALUATE.
        """
        out = []
        in_exec = False
        in_status = False

        for line in lines:
            logical = line.logical

            if not in_exec and not in_status:
                if SQL_START.match(logical):
                    in_exec = True
                    out.append(line)
                    if SQL_END.search(logical):
                        in_exec = False
                    continue
                if STATUS_START.match(logical):
                    in_status = True
                    out.append(line)
                    if STATUS_END.search(logical):
                        in_status = False
                    continue
                continue

            out.append(line)
            if in_exec and SQL_END.search(logical):
                in_exec = False
            elif in_status and STATUS_END.search(logical):
                in_status = False

        return out