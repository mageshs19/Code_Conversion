# LOCATION: src/idms_db2_phase2/generators/cursor_paragraph/cursor_paragraph_body_builder.py
# ACTION: CREATE NEW FILE

"""Builds the COBOL body of a cursor OPEN / FETCH / CLOSE paragraph.

This class owns no COBOL layout literals: every token, indent and template
lives in rules/cursor_paragraph_rules.py. Only dynamic values (cursor name,
paragraph name, host variables) are substituted here.
"""

from __future__ import annotations

from rules.cursor_paragraph_rules import (
    CLOSE_STATEMENT_TEMPLATE,
    CURSOR_EOC_SUFFIX,
    CURSOR_NOT_EOC_SUFFIX,
    DISPLAY_ERROR_TEMPLATE,
    ERROR_CLOSE_TEMPLATE,
    ERROR_FETCH_TEMPLATE,
    ERROR_OPEN_TEMPLATE,
    FETCH_STATEMENT_TEMPLATE,
    IND_SQL_BODY,
    IND_SQL_INTO,
    IND_SQL_INTO_NEXT,
    IND_STATEMENT,
    IND_WHEN,
    IND_WHEN_BODY,
    LONE_PERIOD,
    OPEN_STATEMENT_TEMPLATE,
    PARAGRAPH_HEADER_TEMPLATE,
    PERFORM_TEMPLATE,
    SET_EOC_TEMPLATE,
    SET_NOT_EOC_TEMPLATE,
    SQL_LOCATION_FIELD,
    SQL_LOCATION_NAME_TEMPLATE,
    SQL_LOCATION_NUMBER_PAD,
    SQL_LOCATION_NUMBER_TEMPLATE,
    SQL_LOCATION_USES_PARAGRAPH_NUMBER,
    TOKEN_CONTINUE,
    TOKEN_END_EVALUATE,
    TOKEN_END_EXEC,
    TOKEN_EVALUATE_SQLCODE,
    TOKEN_EXEC_SQL,
    TOKEN_HOST_SEPARATOR,
    TOKEN_INTO,
    TOKEN_WHEN_100,
    TOKEN_WHEN_OTHER,
    TOKEN_WHEN_ZERO,
)


class CursorParagraphBodyBuilder:

    def open_paragraph(
        self,
        cursor_name: str,
        paragraph_name: str,
        sql_error_paragraph: str,
    ) -> list[str]:
        lines = self._paragraph_prologue(
            paragraph_name=paragraph_name,
            statement=OPEN_STATEMENT_TEMPLATE.format(cursor=cursor_name),
        )

        lines.extend(
            [
                f"{IND_STATEMENT}{TOKEN_EVALUATE_SQLCODE}",
                f"{IND_WHEN}{TOKEN_WHEN_ZERO}",
                IND_WHEN_BODY
                + SET_NOT_EOC_TEMPLATE.format(
                    cursor=cursor_name,
                    suffix=CURSOR_NOT_EOC_SUFFIX,
                ),
            ]
        )

        lines.extend(
            self.sqlcode_error_tail(
                error_text=ERROR_OPEN_TEMPLATE.format(cursor=cursor_name),
                sql_error_paragraph=sql_error_paragraph,
            )
        )

        return lines

    def fetch_paragraph(
        self,
        cursor_name: str,
        paragraph_name: str,
        host_variables: list[str],
        sql_error_paragraph: str,
    ) -> list[str]:
        lines = self._paragraph_prologue(
            paragraph_name=paragraph_name,
            statement=FETCH_STATEMENT_TEMPLATE.format(cursor=cursor_name),
            close_exec=False,
        )

        if host_variables:
            lines.extend(self.fetch_into_lines(host_variables))

        lines.extend(
            [
                f"{IND_STATEMENT}{TOKEN_END_EXEC}",
                "",
                f"{IND_STATEMENT}{TOKEN_EVALUATE_SQLCODE}",
                f"{IND_WHEN}{TOKEN_WHEN_ZERO}",
                f"{IND_WHEN_BODY}{TOKEN_CONTINUE}",
                f"{IND_WHEN}{TOKEN_WHEN_100}",
                IND_WHEN_BODY
                + SET_EOC_TEMPLATE.format(
                    cursor=cursor_name,
                    suffix=CURSOR_EOC_SUFFIX,
                ),
            ]
        )

        lines.extend(
            self.sqlcode_error_tail(
                error_text=ERROR_FETCH_TEMPLATE.format(cursor=cursor_name),
                sql_error_paragraph=sql_error_paragraph,
            )
        )

        return lines

    def close_paragraph(
        self,
        cursor_name: str,
        paragraph_name: str,
        sql_error_paragraph: str,
    ) -> list[str]:
        lines = self._paragraph_prologue(
            paragraph_name=paragraph_name,
            statement=CLOSE_STATEMENT_TEMPLATE.format(cursor=cursor_name),
        )

        lines.extend(
            [
                f"{IND_STATEMENT}{TOKEN_EVALUATE_SQLCODE}",
                f"{IND_WHEN}{TOKEN_WHEN_ZERO}",
                f"{IND_WHEN_BODY}{TOKEN_CONTINUE}",
            ]
        )

        lines.extend(
            self.sqlcode_error_tail(
                error_text=ERROR_CLOSE_TEMPLATE.format(cursor=cursor_name),
                sql_error_paragraph=sql_error_paragraph,
            )
        )

        return lines

    def sqlcode_error_tail(
        self,
        error_text: str,
        sql_error_paragraph: str,
    ) -> list[str]:
        """WHEN OTHER branch, END-EVALUATE, then the lone period line.

        Nothing here carries a period. The single period on its own line
        terminates the whole paragraph sentence.
        """
        return [
            f"{IND_WHEN}{TOKEN_WHEN_OTHER}",
            IND_WHEN_BODY + DISPLAY_ERROR_TEMPLATE.format(text=error_text),
            IND_WHEN_BODY
            + PERFORM_TEMPLATE.format(paragraph=sql_error_paragraph),
            f"{IND_STATEMENT}{TOKEN_END_EVALUATE}",
            f"{IND_STATEMENT}{LONE_PERIOD}",
        ]

    def sql_location_move(self, paragraph_name: str) -> str:
        """MOVE the paragraph identity into SQL-LOCATION. No period.

        Manual reference uses the bare paragraph number. Falls back to the
        quoted full name when the paragraph is not number-prefixed.
        """
        name = str(paragraph_name or "").strip()
        number = name.split("-", 1)[0]

        if SQL_LOCATION_USES_PARAGRAPH_NUMBER and number.isdigit():
            return IND_STATEMENT + SQL_LOCATION_NUMBER_TEMPLATE.format(
                number=number,
                pad=SQL_LOCATION_NUMBER_PAD,
                field=SQL_LOCATION_FIELD,
            )

        return IND_STATEMENT + SQL_LOCATION_NAME_TEMPLATE.format(
            name=name,
            field=SQL_LOCATION_FIELD,
        )

    def fetch_into_lines(
        self,
        host_variables: list[str],
    ) -> list[str]:
        """INTO clause in manual form: first host on INTO, leading commas.

            INTO :DCLDZBEFFTV.CO-IDPRKSK-479BEFF
               , :DCLDZBEFFTV.NS-IRMOSTK-479BEFF
        """
        output: list[str] = []

        for index, host in enumerate(host_variables):
            if index == 0:
                output.append(f"{IND_SQL_INTO}{TOKEN_INTO} {host}")
                continue

            output.append(f"{IND_SQL_INTO_NEXT}{TOKEN_HOST_SEPARATOR}{host}")

        return output

    def _paragraph_prologue(
        self,
        paragraph_name: str,
        statement: str,
        close_exec: bool = True,
    ) -> list[str]:
        """Header, SQL-LOCATION move and the EXEC SQL opening."""
        lines = [
            PARAGRAPH_HEADER_TEMPLATE.format(paragraph=paragraph_name),
            self.sql_location_move(paragraph_name),
            "",
            f"{IND_STATEMENT}{TOKEN_EXEC_SQL}",
            f"{IND_SQL_BODY}{statement}",
        ]

        if close_exec:
            lines.append(f"{IND_STATEMENT}{TOKEN_END_EXEC}")
            lines.append("")

        return lines