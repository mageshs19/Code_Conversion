"""CHK-11 SQLCODE and COMMIT conversion."""

from __future__ import annotations

from code_review.engine import sql_blocks as sql
from code_review.engine.check_base import MAJOR, Check
from code_review.standards import cobol_standards as std

EVALUATE_ANY = "EVALUATE"
PERIOD = "."


class SqlcodeCommitConversionCheck(Check):
    CHECK_ID = "CHK-11"
    TITLE = "SQLCODE and COMMIT conversion"
    SEVERITY = MAJOR
    ORDER = 110

    def relevant(self, ctx, view) -> bool:
        return view.has_code_token(std.SQL_BLOCK_START)

    def not_relevant_reason(self) -> str:
        return "Program contains no embedded SQL."

    def review(self, ctx, view, record):
        lines = list(view.code)
        code = [sql.norm(line.logical) for line in lines]
        blocks = sql.sql_blocks(view)

        executable = [
            b for b in blocks
            if b.verb in std.EXECUTABLE_SQL_VERBS
            and b.verb not in std.SQLCODE_EXEMPT_VERBS
        ]
        spans = self._evaluate_spans(code)
        sql_indexes = self._sql_block_indexes(blocks)

        # ---- 01 no legacy SQLCODE form ------------------------------
        record.expect_none(
            "01", "No legacy SQLCODE test remains",
            [
                line for line in lines
                if any(
                    form in sql.norm(line.logical)
                    for form in std.LEGACY_SQLCODE_FORMS
                )
            ],
        )

        # ---- 02 EVALUATE SQLCODE is the standard form ---------------
        if not std.USE_EVALUATE_SQLCODE:
            record.skip(
                "02", f"SQLCODE handling uses {std.SQLCODE_EVALUATE_START}",
                "Not enforced by the site standard.",
            )
        elif not executable:
            record.skip(
                "02", f"SQLCODE handling uses {std.SQLCODE_EVALUATE_START}",
                "Program contains no executable SQL.",
            )
        else:
            record.expect(
                "02", f"SQLCODE handling uses {std.SQLCODE_EVALUATE_START}",
                bool(spans),
                note="No EVALUATE SQLCODE block found.",
            )

        # ---- 03 every EVALUATE SQLCODE closes -----------------------
        #
        # Scope is resolved by walking forward with a depth counter. A
        # plain count of END-EVALUATE lines is wrong: the generated date
        # realignment emits EVALUATE TRUE ... END-EVALUATE, so closes
        # outnumber the SQLCODE opens even when every block is balanced.
        if not spans:
            record.skip(
                "03", f"Every {std.SQLCODE_EVALUATE_START} block is closed",
                "No EVALUATE SQLCODE block found.",
            )
        else:
            record.expect_all(
                "03", f"Every {std.SQLCODE_EVALUATE_START} block is closed",
                [
                    f"line {lines[start].number} opens an unclosed block"
                    for start, end in spans
                    if end < 0
                ],
            )

        # ---- 04 every EVALUATE has WHEN OTHER -----------------------
        if not spans:
            record.skip(
                "04", f"Every SQLCODE block handles "
                      f"{std.SQLCODE_WHEN_OTHER}",
                "No EVALUATE SQLCODE block found.",
            )
        else:
            record.expect_all(
                "04", f"Every SQLCODE block handles "
                      f"{std.SQLCODE_WHEN_OTHER}",
                [
                    f"line {lines[start].number}"
                    for start, end in spans
                    if not self._span_has(
                        code, start, end, std.SQLCODE_WHEN_OTHER,
                    )
                ],
            )

        # ---- 05 WHEN OTHER routes to the error paragraph ------------
        if not spans:
            record.skip(
                "05", f"{std.SQLCODE_WHEN_OTHER} performs "
                      f"{std.SQL_ERROR_PARAGRAPH}",
                "No EVALUATE SQLCODE block found.",
            )
        else:
            perform = f"PERFORM {std.SQL_ERROR_PARAGRAPH}"
            record.expect_all(
                "05", f"{std.SQLCODE_WHEN_OTHER} performs "
                      f"{std.SQL_ERROR_PARAGRAPH}",
                [
                    f"line {lines[start].number}"
                    for start, end in spans
                    if not self._span_has(code, start, end, perform)
                ],
            )

        # ---- 06 every executable SQL block is checked ---------------
        if not executable:
            record.skip(
                "06", "Every executable SQL block checks SQLCODE",
                "Program contains no executable SQL.",
            )
        else:
            record.expect_none(
                "06", "Every executable SQL block checks SQLCODE",
                [b for b in executable if not self._checked_after(view, b)],
            )

        # ---- 07 end of cursor uses SQLCODE = 100 --------------------
        if not any(b.verb == "FETCH" for b in blocks):
            record.skip(
                "07", f"End of cursor uses {std.END_OF_CURSOR_CONDITION}",
                "Program contains no cursor FETCH.",
            )
        else:
            record.expect(
                "07", f"End of cursor uses {std.END_OF_CURSOR_CONDITION}",
                view.has_code_token(std.END_OF_CURSOR_CONDITION)
                or any(
                    line.startswith(std.SQLCODE_NOT_FOUND_BRANCH)
                    for line in code
                ),
                note="Neither SQLCODE = 100 nor WHEN 100 found.",
            )

        # ---- 08 FINISH became COMMIT --------------------------------
        source = sql.norm(ctx.source_cobol)
        if not ctx.has_source:
            record.skip(
                "08", f"{std.IDMS_COMMIT_VERB} converted to "
                      f"{std.COMMIT_STATEMENT}",
                "No source program supplied for comparison.",
            )
        elif std.IDMS_COMMIT_VERB not in source:
            record.skip(
                "08", f"{std.IDMS_COMMIT_VERB} converted to "
                      f"{std.COMMIT_STATEMENT}",
                f"Source contains no {std.IDMS_COMMIT_VERB} statement.",
            )
        else:
            record.expect(
                "08", f"{std.IDMS_COMMIT_VERB} converted to "
                      f"{std.COMMIT_STATEMENT}",
                any(b.verb == std.COMMIT_STATEMENT for b in blocks),
                note=f"Source has {std.IDMS_COMMIT_VERB} but no generated "
                     f"{std.COMMIT_STATEMENT} block was found.",
            )

        # ---- 09 no period inside an EVALUATE block ------------------
        #
        # In COBOL a period terminates the sentence and closes every open
        # scope. A period on a statement inside EVALUATE therefore ends
        # the EVALUATE early and leaves END-EVALUATE with no matching
        # opener, which the compiler rejects.
        if not std.ENFORCE_NO_PERIOD_IN_EVALUATE:
            record.skip(
                "09", f"No period terminates a statement inside "
                      f"{std.SQLCODE_EVALUATE_START}",
                "Not enforced by the site standard.",
            )
        elif not spans:
            record.skip(
                "09", f"No period terminates a statement inside "
                      f"{std.SQLCODE_EVALUATE_START}",
                "No EVALUATE SQLCODE block found.",
            )
        else:
            record.expect_none(
                "09", f"No period terminates a statement inside "
                      f"{std.SQLCODE_EVALUATE_START}",
                self._interior_periods(lines, code, spans, sql_indexes),
            )

    # ---- helpers ----------------------------------------------------
    @staticmethod
    def _evaluate_spans(code: list[str]) -> list[tuple[int, int]]:
        """Start and end index of each EVALUATE SQLCODE block.

        End is -1 when the block never closes. Nested EVALUATE blocks of
        any kind are counted, so an inner EVALUATE TRUE cannot be mistaken
        for the outer block's terminator.
        """
        spans: list[tuple[int, int]] = []
        for index, line in enumerate(code):
            if not line.startswith(std.SQLCODE_EVALUATE_START):
                continue
            depth = 0
            end = -1
            for cursor in range(index, len(code)):
                current = code[cursor]
                if current.startswith(std.SQLCODE_EVALUATE_END):
                    depth -= 1
                    if depth <= 0:
                        end = cursor
                        break
                elif current.startswith(EVALUATE_ANY):
                    depth += 1
            spans.append((index, end))
        return spans

    @staticmethod
    def _sql_block_indexes(blocks) -> set[int]:
        """Code indexes occupied by EXEC SQL blocks.

        END-EXEC. legitimately carries a period, so those lines must not
        be reported by criterion 09.
        """
        out: set[int] = set()
        for block in blocks:
            out.update(range(block.first_index, block.last_index + 1))
        return out

    @staticmethod
    def _interior_periods(
        lines: list,
        code: list[str],
        spans: list[tuple[int, int]],
        sql_indexes: set[int],
    ) -> list:
        """Lines inside an EVALUATE that end with a period."""
        out: list = []
        seen: set[int] = set()

        for start, end in spans:
            stop = end if end >= 0 else len(code)
            for index in range(start + 1, stop):
                if index in sql_indexes or index in seen:
                    continue
                if code[index].endswith(PERIOD):
                    seen.add(index)
                    out.append(lines[index])
        return out

    @staticmethod
    def _span_has(code: list[str], start: int, end: int, token: str) -> bool:
        stop = end if end >= 0 else len(code)
        wanted = sql.norm(token)
        return any(wanted in line for line in code[start + 1:stop])

    @staticmethod
    def _checked_after(view, block) -> bool:
        window = sql.lines_after(view, block, std.SQLCODE_LOOKAHEAD)
        return any(
            line.startswith(std.SQLCODE_EVALUATE_START)
            or line.startswith("IF SQLCODE")
            or line.startswith(std.SQLCODE_NOT_FOUND_BRANCH)
            for line in window
        )