from __future__ import annotations

from patterns.fixed_format_patterns import DIVISION_PATTERN, SEQUENCE_ONLY_PATTERN
from rules.fixed_format_rules import (
    BODY_WIDTH,
    COMMENT_INDICATOR,
    DEBUG_INDICATOR,
    DEBUG_INDICATOR_LOWER,
    FIXED_FORMAT_MESSAGES,
    PAGE_INDICATOR,
    PROCEDURE_DIVISION_NAME,
    SPACE_INDICATOR,
    TOTAL_WIDTH,
    VALID_INDICATORS,
)


class FixedFormatLineComposer:
    """Per-line composition: parse, area-body, wrap, sequence, compose.

    Depends on the host class for ``self.line_parser``, ``self.body_formatter``,
    and ``self.wrapper``. Layout constants and patterns are external.
    """

    def _compose_body_lines(
        self,
        *,
        raw_text: str,
        state,
        current_division: str,
        inside_exec_sql: bool,
        previous_procedure_indent: str,
        preserve_blank_lines: bool,
        output_lines: list[str],
    ) -> tuple[str, bool, str]:
        """Process one raw line, appending composed lines to output_lines.

        Returns the updated (current_division, inside_exec_sql,
        previous_procedure_indent) tuple.
        """
        if SEQUENCE_ONLY_PATTERN.match(raw_text.strip()):
            return current_division, inside_exec_sql, previous_procedure_indent

        parsed = self.line_parser.parse_line(raw_text)
        indicator = str(parsed["indicator"])
        body = str(parsed["body"])
        logical = body.strip()

        if not body.strip() and indicator == SPACE_INDICATOR:
            self._append_blank(state, preserve_blank_lines, output_lines)
            return current_division, inside_exec_sql, previous_procedure_indent

        division_match = DIVISION_PATTERN.match(logical)
        if division_match:
            current_division = division_match.group(1).upper()
            previous_procedure_indent = " "

        if self.body_formatter.is_exec_sql_start(logical):
            inside_exec_sql = True

        area_body = self.body_formatter.area_body(
            body=body,
            logical=logical,
            current_division=current_division,
            inside_exec_sql=inside_exec_sql,
            indicator=indicator,
            previous_procedure_indent=previous_procedure_indent,
        )

        physical_bodies = self.wrapper.wrap_body(
            body=area_body,
            indicator=indicator,
            inside_exec_sql=inside_exec_sql,
            current_division=current_division,
            previous_procedure_indent=previous_procedure_indent,
        )
        physical_bodies = self.wrapper.repair_boolean_operator_only_lines(
            physical_bodies
        )

        for index, physical_body in enumerate(physical_bodies):
            physical_indicator = (
                self._continuation_indicator(indicator) if index > 0 else indicator
            )
            output_lines.append(
                self._compose_line(
                    left_seq=state.current_left(),
                    indicator=physical_indicator,
                    area_body=physical_body,
                    right_seq=state.current_right(),
                )
            )
            state.advance()

        if (
            current_division == PROCEDURE_DIVISION_NAME
            and indicator == SPACE_INDICATOR
            and physical_bodies
            and not self.body_formatter.is_area_a_statement(logical)
        ):
            previous_procedure_indent = self.body_formatter.leading_spaces(
                physical_bodies[0],
                default=" ",
            )

        if self.body_formatter.is_exec_sql_end(logical):
            inside_exec_sql = False

        return current_division, inside_exec_sql, previous_procedure_indent

    def _append_blank(self, state, preserve_blank_lines, output_lines) -> None:
        if not preserve_blank_lines:
            return
        output_lines.append(
            self._compose_line(
                left_seq=state.current_left(),
                indicator=SPACE_INDICATOR,
                area_body="",
                right_seq=state.current_right(),
            )
        )
        state.advance()

    def _continuation_indicator(self, indicator: str) -> str:
        if indicator in {COMMENT_INDICATOR, PAGE_INDICATOR}:
            return indicator
        if indicator in {DEBUG_INDICATOR, DEBUG_INDICATOR_LOWER}:
            return DEBUG_INDICATOR
        return SPACE_INDICATOR

    def _compose_line(
        self,
        left_seq: str,
        indicator: str,
        area_body: str,
        right_seq: str,
    ) -> str:
        """Assemble one 80-column record.

        CORRECTION - silent truncation
        ------------------------------
        This method used to do

            if len(safe_body) > BODY_WIDTH:
                safe_body = safe_body[:BODY_WIDTH]

        with no report. Every caller reaches here through
        FixedFormatWrapper.wrap_body(), which is responsible for
        splitting an over-long body, so a body arriving over-width means
        wrapping already failed. Cutting it hid that failure and
        produced an undefined data name.

        The cut is retained as the last line of defence - emitting a
        record longer than 80 columns would be worse - but it is now
        REPORTED, so it can never again be invisible.
        """
        safe_left = str(left_seq or "").zfill(6)[-6:]
        safe_right = str(right_seq or "").zfill(8)[-8:]
        safe_indicator = str(indicator or SPACE_INDICATOR)[:1]

        if safe_indicator not in VALID_INDICATORS:
            safe_indicator = SPACE_INDICATOR
        if safe_indicator == DEBUG_INDICATOR_LOWER:
            safe_indicator = DEBUG_INDICATOR

        safe_body = str(area_body or "").rstrip()

        if len(safe_body) > BODY_WIDTH:
            messages = getattr(self, "messages", None)
            if messages is not None:
                template = FIXED_FORMAT_MESSAGES.get("body_truncated", "")
                if template:
                    messages.append(
                        template.format(
                            width=len(safe_body),
                            limit=BODY_WIDTH,
                            body=safe_body.strip()[:40],
                        )
                    )
            safe_body = safe_body[:BODY_WIDTH]

        body_area = safe_body.ljust(BODY_WIDTH)
        line = f"{safe_left}{safe_indicator}{body_area}{safe_right}"

        if len(line) > TOTAL_WIDTH:
            return line[:TOTAL_WIDTH]
        if len(line) < TOTAL_WIDTH:
            return line.ljust(TOTAL_WIDTH)
        return line