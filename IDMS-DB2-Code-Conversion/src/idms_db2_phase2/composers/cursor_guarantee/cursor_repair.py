# LOCATION: src/idms_db2_phase2/composers/cursor_guarantee/cursor_repair.py
# ACTION: CREATE NEW FILE

"""Every mutation this pass performs.

Four repairs, each independently safe to skip:

  normalise_perform_line   legacy exit test  -> cursor EOC flag
  normalise_loop           same, UNTIL on its own line
  guarantee_close          insert the missing PERFORM <close>
  synthesise_loop          build the whole driving shape from scratch

Nothing here decides WHICH repair a cursor needs - that is the
composer's single responsibility.
"""

from __future__ import annotations

from idms_db2_phase2.composers.cursor_guarantee.cursor_lines import CursorLines
from idms_db2_phase2.composers.cursor_guarantee.cursor_models import (
    CONTINUE_PATTERN,
    UNTIL_ONLY_PATTERN,
    WHEN_ZERO_PATTERN,
    CursorParagraphSet,
    CursorPerform,
    LoopShape,
    MessageLog,
)
from rules.cursor_close_guarantee_rules import (
    ENFORCE_FETCH_DRIVES_BUSINESS_PARAGRAPH,
    EXIT_PARAGRAPH_SUFFIX,
    PERFORM_BUSINESS_TEMPLATE,
    PERFORM_BUSINESS_THRU_TEMPLATE,
    PERFORM_CLOSE_TEMPLATE,
    PERFORM_FETCH_UNTIL_TEMPLATE,
    PREFER_THRU_EXIT_PARAGRAPH,
    STATEMENT_TERMINATOR,
    UNTIL_TEMPLATE,
)


class CursorRepair:
    """Rewrites, inserts and deletes. Owns no path selection."""

    def __init__(
        self,
        lines_utils: CursorLines | None = None,
        log: MessageLog | None = None,
    ) -> None:
        self.lines_utils = lines_utils or CursorLines()
        self.log = log or MessageLog()

    # =================================================================
    # Exit-condition normalisation
    # =================================================================
    def normalise_perform_line(
        self,
        lines: list[str],
        index: int,
        condition: str,
        cursor: str,
    ) -> list[str]:
        """Rewrite the UNTIL tail of a PERFORM <fetch> UNTIL <cond> line."""
        if not 0 <= index < len(lines):
            return lines

        logical = self.lines_utils.logical(lines[index])
        head, _separator, tail = self.lines_utils.partition_until(logical)

        if not tail:
            return lines

        current = tail.rstrip(STATEMENT_TERMINATOR).strip()

        if self.lines_utils.compress(current) == self.lines_utils.compress(
            condition
        ):
            return lines

        if not self.lines_utils.is_legacy_condition(current):
            return lines

        body = f"{head.rstrip()} {UNTIL_TEMPLATE.format(condition=condition)}"

        if logical.rstrip().endswith(STATEMENT_TERMINATOR):
            body = f"{body}{STATEMENT_TERMINATOR}"

        return self._rewrite(lines, index, body, cursor, condition)

    def normalise_loop(
        self,
        lines: list[str],
        loop: LoopShape,
        condition: str,
        cursor: str,
    ) -> list[str]:
        """Rewrite a legacy loop exit condition to the cursor EOC flag."""
        index = loop.until_index

        if not 0 <= index < len(lines):
            return lines

        if self.lines_utils.compress(loop.condition) == (
            self.lines_utils.compress(condition)
        ):
            return lines

        if not self.lines_utils.is_legacy_condition(loop.condition):
            return lines

        logical = self.lines_utils.logical(lines[index])

        if UNTIL_ONLY_PATTERN.match(logical):
            body = UNTIL_TEMPLATE.format(condition=condition)
        else:
            head, _separator, _tail = self.lines_utils.partition_until(logical)
            body = (
                f"{head.rstrip()} "
                f"{UNTIL_TEMPLATE.format(condition=condition)}"
            )

        if loop.terminated:
            body = f"{body}{STATEMENT_TERMINATOR}"

        return self._rewrite(lines, index, body, cursor, condition)

    def _rewrite(
        self,
        lines: list[str],
        index: int,
        body: str,
        cursor: str,
        condition: str,
    ) -> list[str]:
        output = list(lines)
        output[index] = self.lines_utils.format_like(output[index], body)
        self.log.log("condition_rewritten", cursor=cursor, condition=condition)
        return output

    # =================================================================
    # CLOSE guarantee
    # =================================================================
    def guarantee_close(
        self,
        lines: list[str],
        after_index: int,
        cursor_set: CursorParagraphSet,
        close_performs: list[CursorPerform],
    ) -> list[str]:
        if close_performs:
            self.log.log("close_present", close=cursor_set.close_name)
            return lines

        if not 0 <= after_index < len(lines):
            return lines

        close_line = self.lines_utils.format_like(
            lines[after_index],
            PERFORM_CLOSE_TEMPLATE.format(close=cursor_set.close_name),
        )

        output = list(lines)
        output.insert(after_index + 1, close_line)

        self.log.log(
            "close_inserted",
            close=cursor_set.close_name,
            cursor=cursor_set.cursor,
        )

        return output

    # =================================================================
    # Loop synthesis
    # =================================================================
    def synthesise_loop(
        self,
        lines: list[str],
        cursor_set: CursorParagraphSet,
        priming: CursorPerform,
        repeats: list[CursorPerform],
        business: str,
        close_performs: list[CursorPerform],
        eoc_condition: str,
    ) -> list[str]:
        """Build OPEN / FETCH-UNTIL / CLOSE and drive the business para.

        Step 2 runs before step 3 because deleting a line BELOW the
        priming fetch cannot move it, while inserting above it would
        move every repeat index.
        """
        output = list(lines)

        # 1. Bind the FETCH paragraph to the business paragraph.
        if business and ENFORCE_FETCH_DRIVES_BUSINESS_PARAGRAPH:
            output = self.bind_fetch_to_business(
                lines=output,
                fetch_paragraph=cursor_set.fetch_name,
                business=business,
            )
        elif not business:
            self.log.log("business_paragraph_unknown", cursor=cursor_set.cursor)

        # 2. Remove every orphan repeat fetch, highest index first.
        for repeat in sorted(repeats, key=lambda item: item.index, reverse=True):
            output = self.remove_statement(output, repeat.index)
            self.log.log("repeat_fetch_removed", fetch=repeat.paragraph)

        # 3. Replace the priming fetch with the loop, plus the CLOSE.
        if not 0 <= priming.index < len(output):
            return output

        reference = output[priming.index]

        replacement = [
            self.lines_utils.format_like(
                reference,
                PERFORM_FETCH_UNTIL_TEMPLATE.format(
                    fetch=cursor_set.fetch_name,
                    condition=eoc_condition,
                ),
            )
        ]

        if close_performs:
            self.log.log("close_present", close=cursor_set.close_name)
        else:
            replacement.append(
                self.lines_utils.format_like(
                    reference,
                    PERFORM_CLOSE_TEMPLATE.format(close=cursor_set.close_name),
                )
            )

        output[priming.index : priming.index + 1] = replacement

        self.log.log(
            "loop_synthesised",
            cursor=cursor_set.cursor,
            fetch=cursor_set.fetch_name,
            condition=eoc_condition,
            close=cursor_set.close_name,
        )

        return output

    def bind_fetch_to_business(
        self,
        lines: list[str],
        fetch_paragraph: str,
        business: str,
    ) -> list[str]:
        """Rewrite WHEN ZERO / CONTINUE inside the FETCH paragraph."""
        headers = self.lines_utils.paragraph_headers(lines)
        span = self.lines_utils.paragraph_span(
            headers, fetch_paragraph, len(lines)
        )

        if span is None:
            return lines

        start, end = span
        output = list(lines)
        body = self._business_body(headers, business)

        index = start
        while index < end:
            logical = self.lines_utils.logical(output[index])

            if not WHEN_ZERO_PATTERN.match(logical):
                index += 1
                continue

            target = self.lines_utils.next_executable_index(
                output, index + 1, end
            )

            if target < 0:
                index += 1
                continue

            if not CONTINUE_PATTERN.match(self.lines_utils.logical(output[target])):
                index += 1
                continue

            output[target] = self.lines_utils.format_like(output[target], body)

            self.log.log(
                "business_paragraph_bound",
                fetch=fetch_paragraph,
                paragraph=business,
            )

            index = target + 1

        return output

    @staticmethod
    def _business_body(headers, business: str) -> str:
        body = PERFORM_BUSINESS_TEMPLATE.format(paragraph=business)

        if not PREFER_THRU_EXIT_PARAGRAPH:
            return body

        exit_name = f"{business}{EXIT_PARAGRAPH_SUFFIX}"

        if any(header.name == exit_name for header in headers):
            return PERFORM_BUSINESS_THRU_TEMPLATE.format(
                paragraph=business,
                through=exit_name,
            )

        return body

    # =================================================================
    # Statement removal
    # =================================================================
    def remove_statement(
        self,
        lines: list[str],
        index: int,
    ) -> list[str]:
        """Delete one statement without orphaning its COBOL sentence."""
        if not 0 <= index < len(lines):
            return lines

        removed = self.lines_utils.logical(lines[index])
        carried_period = removed.rstrip().endswith(STATEMENT_TERMINATOR)

        output = list(lines)
        del output[index]

        if not carried_period:
            return output

        previous = self.lines_utils.previous_executable_index(output, index - 1)

        if previous < 0:
            return output

        previous_logical = self.lines_utils.logical(output[previous])

        if previous_logical.rstrip().endswith(STATEMENT_TERMINATOR):
            return output

        output[previous] = self.lines_utils.format_like(
            output[previous],
            f"{previous_logical.rstrip()}{STATEMENT_TERMINATOR}",
        )

        return output


__all__ = ["CursorRepair"]