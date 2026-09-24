# LOCATION: src/idms_db2_phase2/composers/cursor_close_guarantee/loop_synthesiser.py
# ACTION: CREATE NEW FILE

"""Builds the manual OPEN / FETCH-UNTIL / CLOSE shape from scratch.

Used only when no driving loop exists at all. Three edits, applied so
that no earlier index is invalidated by a later one:

    1. bind the FETCH paragraph WHEN ZERO branch to the business
       paragraph that used to carry the OBTAIN NEXT,
    2. delete every orphan repeat PERFORM <fetch>, highest index first,
    3. replace the priming PERFORM <fetch>. with the driving loop and,
       when needed, the CLOSE.

Step 2 runs before step 3 because deleting a line below the priming
fetch cannot move the priming fetch, while inserting above it would move
every repeat.
"""

from __future__ import annotations

from idms_db2_phase2.composers.cursor_close_guarantee.line_utils import (
    CursorGuaranteeLineUtils,
)
from idms_db2_phase2.composers.cursor_close_guarantee.message_log import (
    MessageLog,
)
from idms_db2_phase2.composers.cursor_close_guarantee.models import (
    CursorParagraphSet,
    CursorPerform,
)
from idms_db2_phase2.composers.cursor_close_guarantee.paragraph_index import (
    ParagraphIndex,
)
from patterns.cursor_close_guarantee_patterns import (
    CONTINUE_PATTERN,
    WHEN_ZERO_PATTERN,
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
)


class LoopSynthesiser:
    """Creates the manual driving-loop shape for an undriven cursor."""

    def __init__(
        self,
        line_utils: CursorGuaranteeLineUtils | None = None,
        paragraph_index: ParagraphIndex | None = None,
        log: MessageLog | None = None,
    ) -> None:
        self.lines_utils = line_utils or CursorGuaranteeLineUtils()
        self.paragraphs = paragraph_index or ParagraphIndex(self.lines_utils)
        self.log = log or MessageLog()

    #
    # Public entry point
    #
    def synthesise(
        self,
        lines: list[str],
        cursor_set: CursorParagraphSet,
        priming: CursorPerform,
        repeats: list[CursorPerform],
        business: str,
        close_performs: list[CursorPerform],
        eoc_condition: str,
    ) -> list[str]:
        output = list(lines)

        # 1. Bind the FETCH paragraph to the business paragraph.
        if business and ENFORCE_FETCH_DRIVES_BUSINESS_PARAGRAPH:
            output = self._bind_fetch_to_business(
                lines=output,
                fetch_paragraph=cursor_set.fetch_name,
                business=business,
            )
        elif not business:
            self.log.log(
                "business_paragraph_unknown",
                cursor=cursor_set.cursor,
            )

        # 2. Remove every orphan repeat fetch, highest index first.
        for repeat in sorted(repeats, key=lambda item: item.index, reverse=True):
            output = self._remove_statement(output, repeat.index)
            self.log.log("repeat_fetch_removed", fetch=repeat.paragraph)

        # 3. Replace the priming fetch with the loop plus the CLOSE.
        return self._write_driving_loop(
            lines=output,
            cursor_set=cursor_set,
            priming_index=priming.index,
            close_performs=close_performs,
            eoc_condition=eoc_condition,
        )

    #
    # Step 1
    #
    def _bind_fetch_to_business(
        self,
        lines: list[str],
        fetch_paragraph: str,
        business: str,
    ) -> list[str]:
        """Rewrite WHEN ZERO / CONTINUE inside the FETCH paragraph."""
        headers = self.paragraphs.headers(lines)
        span = self.paragraphs.span(headers, fetch_paragraph, len(lines))

        if span is None:
            return lines

        start, end = span
        output = list(lines)
        body = self._business_body(headers, business)

        index = start
        while index < end:
            if not WHEN_ZERO_PATTERN.match(self.lines_utils.logical(output[index])):
                index += 1
                continue

            target = self.paragraphs.next_executable_index(
                output, index + 1, end
            )

            if target < 0:
                index += 1
                continue

            if not CONTINUE_PATTERN.match(self.lines_utils.logical(output[target])):
                index += 1
                continue

            output[target] = self.lines_utils.format_like(
                reference_line=output[target],
                body=body,
            )

            self.log.log(
                "business_paragraph_bound",
                fetch=fetch_paragraph,
                paragraph=business,
            )

            index = target + 1

        return output

    def _business_body(self, headers: list, business: str) -> str:
        """PERFORM <para>, or PERFORM <para> THRU <para>-EXIT when it exists."""
        if PREFER_THRU_EXIT_PARAGRAPH:
            exit_name = f"{business}{EXIT_PARAGRAPH_SUFFIX}"

            if self.paragraphs.exists(headers, exit_name):
                return PERFORM_BUSINESS_THRU_TEMPLATE.format(
                    paragraph=business,
                    through=exit_name,
                )

        return PERFORM_BUSINESS_TEMPLATE.format(paragraph=business)

    #
    # Step 2
    #
    def _remove_statement(
        self,
        lines: list[str],
        index: int,
    ) -> list[str]:
        """Delete one statement without orphaning its COBOL sentence."""
        if not 0 <= index < len(lines):
            return lines

        carried_period = self.lines_utils.is_terminated(
            self.lines_utils.logical(lines[index])
        )

        output = list(lines)
        del output[index]

        if not carried_period:
            return output

        previous = self.paragraphs.previous_executable_index(output, index - 1)

        if previous < 0:
            return output

        previous_logical = self.lines_utils.logical(output[previous])

        if self.lines_utils.is_terminated(previous_logical):
            return output

        output[previous] = self.lines_utils.format_like(
            reference_line=output[previous],
            body=f"{previous_logical.rstrip()}{STATEMENT_TERMINATOR}",
        )

        return output

    #
    # Step 3
    #
    def _write_driving_loop(
        self,
        lines: list[str],
        cursor_set: CursorParagraphSet,
        priming_index: int,
        close_performs: list[CursorPerform],
        eoc_condition: str,
    ) -> list[str]:
        if not 0 <= priming_index < len(lines):
            return lines

        output = list(lines)
        reference = output[priming_index]

        replacement = [
            self.lines_utils.format_like(
                reference_line=reference,
                body=PERFORM_FETCH_UNTIL_TEMPLATE.format(
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
                    reference_line=reference,
                    body=PERFORM_CLOSE_TEMPLATE.format(
                        close=cursor_set.close_name,
                    ),
                )
            )

        output[priming_index : priming_index + 1] = replacement

        self.log.log(
            "loop_synthesised",
            cursor=cursor_set.cursor,
            fetch=cursor_set.fetch_name,
            condition=eoc_condition,
            close=cursor_set.close_name,
        )

        return output


__all__ = ["LoopSynthesiser"]