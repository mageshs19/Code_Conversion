# LOCATION: src/idms_db2_phase2/generators/cursor_paragraph/cursor_paragraph_body_builder.py
# ACTION: REPLACE ENTIRE FILE

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
    EMIT_FETCH_KEY_DIAGNOSTICS,
    ENFORCE_FETCH_PROLOGUE,
    ENFORCE_SQL_LOCATION_IN_ERROR_BRANCH,
    ERROR_CLOSE_TEMPLATE,
    ERROR_FETCH_TEMPLATE,
    ERROR_OPEN_TEMPLATE,
    FETCH_KEY_BODY_END_COLUMN,
    FETCH_KEY_DIAGNOSTIC_LIMIT,
    FETCH_KEY_DISPLAY_TEMPLATE,
    FETCH_KEY_HOST_TEMPLATE,
    FETCH_KEY_LABEL_WIDTH,
    FETCH_STATEMENT_TEMPLATE,
    HOST_GROUP_SEPARATOR,
    HOST_REFERENCE_PREFIX,
    IND_SQL_BODY,
    IND_SQL_INTO,
    IND_SQL_INTO_NEXT,
    IND_STATEMENT,
    IND_WHEN,
    IND_WHEN_BODY,
    IND_WHEN_BODY_CONT,
    INITIALIZE_HOST_GROUP_TEMPLATE,
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

    # ------------------------------------------------------------------
    # OPEN
    # ------------------------------------------------------------------
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

        # No diagnostic_hosts: OPEN has not fetched a row, so there is
        # nothing row-specific to report.
        lines.extend(
            self.sqlcode_error_tail(
                error_text=ERROR_OPEN_TEMPLATE.format(cursor=cursor_name),
                sql_error_paragraph=sql_error_paragraph,
                paragraph_name=paragraph_name,
            )
        )

        return lines

    # ------------------------------------------------------------------
    # FETCH
    # ------------------------------------------------------------------
    def fetch_paragraph(
        self,
        cursor_name: str,
        paragraph_name: str,
        host_variables: list[str],
        sql_error_paragraph: str,
    ) -> list[str]:
        """FETCH paragraph body.

        CORRECTION - stale host data after a non-zero SQLCODE
        ------------------------------------------------------
        DB2 leaves the host variables UNCHANGED when a FETCH returns
        SQLCODE 100 or a negative code, so without an INITIALIZE the
        DCLGEN group still holds the PREVIOUS row and every downstream
        MOVE ... OF <group> copies stale values into the output record.

        The group is derived from the FETCH INTO list itself rather than
        from a resolver, so it is always the group this very statement
        writes into and no new parameter is needed. When it cannot be
        derived the INITIALIZE is omitted - never emitted empty.
        """
        lines: list[str] = [
            PARAGRAPH_HEADER_TEMPLATE.format(paragraph=paragraph_name),
        ]

        # ---- prologue: clear the host group, re-arm the flag
        if ENFORCE_FETCH_PROLOGUE:
            group = self._host_group(host_variables)

            if group:
                lines.append(
                    IND_STATEMENT
                    + INITIALIZE_HOST_GROUP_TEMPLATE.format(group=group)
                )

            lines.append(
                IND_STATEMENT
                + SET_NOT_EOC_TEMPLATE.format(
                    cursor=cursor_name,
                    suffix=CURSOR_NOT_EOC_SUFFIX,
                )
            )

        # ---- SQL-LOCATION (already carries its own indent)
        lines.append(self.sql_location_move(paragraph_name))
        lines.append("")

        # ---- the FETCH itself
        lines.append(f"{IND_STATEMENT}{TOKEN_EXEC_SQL}")
        lines.append(
            f"{IND_SQL_BODY}"
            f"{FETCH_STATEMENT_TEMPLATE.format(cursor=cursor_name)}"
        )
        lines.extend(self.fetch_into_lines(host_variables))
        lines.append(f"{IND_SQL_BODY}{TOKEN_END_EXEC}")
        lines.append("")

        # ---- EVALUATE SQLCODE
        lines.append(f"{IND_STATEMENT}{TOKEN_EVALUATE_SQLCODE}")
        lines.append(f"{IND_WHEN}{TOKEN_WHEN_ZERO}")
        lines.append(f"{IND_WHEN_BODY}{TOKEN_CONTINUE}")
        lines.append(f"{IND_WHEN}{TOKEN_WHEN_100}")
        lines.append(
            f"{IND_WHEN_BODY}"
            + SET_EOC_TEMPLATE.format(
                cursor=cursor_name,
                suffix=CURSOR_EOC_SUFFIX,
            )
        )

        # FETCH is the ONLY operation that carries diagnostic hosts: it
        # is the only one with a row to identify.
        lines.extend(
            self.sqlcode_error_tail(
                error_text=ERROR_FETCH_TEMPLATE.format(cursor=cursor_name),
                sql_error_paragraph=sql_error_paragraph,
                paragraph_name=paragraph_name,
                diagnostic_hosts=host_variables,
            )
        )

        return lines

    # ------------------------------------------------------------------
    # CLOSE
    # ------------------------------------------------------------------
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

        # No diagnostic_hosts: the row is already gone by CLOSE time.
        lines.extend(
            self.sqlcode_error_tail(
                error_text=ERROR_CLOSE_TEMPLATE.format(cursor=cursor_name),
                sql_error_paragraph=sql_error_paragraph,
                paragraph_name=paragraph_name,
            )
        )

        return lines

    # ------------------------------------------------------------------
    # SQL-LOCATION
    # ------------------------------------------------------------------
    def sql_location_move(self, paragraph_name: str) -> str:
        """MOVE the paragraph identity into SQL-LOCATION. No period.

        Indented as a paragraph-level statement. The unindented form is
        available from sql_location_body() for use inside a WHEN branch.
        """
        return IND_STATEMENT + self.sql_location_body(paragraph_name)

    def sql_location_body(self, paragraph_name: str) -> str:
        """The MOVE ... TO SQL-LOCATION body, with no indent.

        Manual reference uses the bare paragraph number. Falls back to
        the quoted full name when the paragraph is not number-prefixed.
        """
        name = str(paragraph_name or "").strip()
        number = name.split("-", 1)[0]

        if SQL_LOCATION_USES_PARAGRAPH_NUMBER and number.isdigit():
            return SQL_LOCATION_NUMBER_TEMPLATE.format(
                number=number,
                pad=SQL_LOCATION_NUMBER_PAD,
                field=SQL_LOCATION_FIELD,
            )

        return SQL_LOCATION_NAME_TEMPLATE.format(
            name=name,
            field=SQL_LOCATION_FIELD,
        )

    # ------------------------------------------------------------------
    # WHEN OTHER branch
    # ------------------------------------------------------------------
    def sqlcode_error_tail(
        self,
        error_text: str,
        sql_error_paragraph: str,
        paragraph_name: str = "",
        diagnostic_hosts: list[str] | None = None,
    ) -> list[str]:
        """The WHEN OTHER branch of an EVALUATE SQLCODE block.

        `diagnostic_hosts` is optional so OPEN and CLOSE keep their
        existing three-argument call unchanged. Only FETCH has a
        fetched row worth reporting.

        SQL-LOCATION stays FIRST: CHK-09.05, CHK-10.05 and CHK-20.07
        read the first statement of this branch, and the cursor
        contract tests assert it explicitly.
        """
        lines: list[str] = [f"{IND_WHEN}{TOKEN_WHEN_OTHER}"]

        if ENFORCE_SQL_LOCATION_IN_ERROR_BRANCH and paragraph_name:
            lines.append(
                IND_WHEN_BODY + self.sql_location_body(paragraph_name)
            )

        lines.append(
            IND_WHEN_BODY + DISPLAY_ERROR_TEMPLATE.format(text=error_text)
        )

        # Identify the failing row before handing control to SQLERROR.
        lines.extend(self._key_diagnostic_lines(diagnostic_hosts))

        lines.append(
            IND_WHEN_BODY
            + PERFORM_TEMPLATE.format(paragraph=sql_error_paragraph)
        )
        lines.append(f"{IND_STATEMENT}{TOKEN_END_EVALUATE}")
        lines.append(f"{IND_STATEMENT}{LONE_PERIOD}")

        return lines

    # ------------------------------------------------------------------
    # INTO clause
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Shared prologue
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Host group resolution
    # ------------------------------------------------------------------
    @staticmethod
    def _host_group(host_variables: list[str]) -> str:
        """DCLGEN group owning the fetched host variables.

        Read from the FETCH INTO list, so it can never disagree with the
        statement it guards. Three host forms are accepted, because the
        resolver may deliver any of them:

            :DCLDZBFASTV.DA-CPTAFS-479BFAS  ->  DCLDZBFASTV
            DCLDZBFASTV.DA-CPTAFS-479BFAS   ->  DCLDZBFASTV
            DA-CPTAFS-479BFAS OF DCLDZBFASTV->  DCLDZBFASTV

        Returns "" when no group can be read, which makes the caller skip
        the INITIALIZE rather than emit 'INITIALIZE .' - invalid COBOL.
        """
        for host in host_variables or []:
            text = str(host or "").strip()

            if text.startswith(HOST_REFERENCE_PREFIX):
                text = text[len(HOST_REFERENCE_PREFIX):].strip()

            if HOST_GROUP_SEPARATOR in text:
                group = text.split(HOST_GROUP_SEPARATOR, 1)[0].strip()
                if group:
                    return group

            upper = text.upper()
            if " OF " in upper:
                group = text[upper.rindex(" OF ") + 4:].strip()
                if group:
                    return group

        return ""

    # ------------------------------------------------------------------
    # FETCH error-branch key diagnostics
    # ------------------------------------------------------------------
    def _key_diagnostic_lines(
        self,
        host_variables: list[str] | None,
    ) -> list[str]:
        """DISPLAY the leading fetched columns.

        Hosts come from the FETCH INTO list this paragraph already
        carries, so the displayed names can never disagree with the
        statement that failed.
        """
        if not EMIT_FETCH_KEY_DIAGNOSTICS:
            return []

        pairs = self._host_pairs(host_variables)
        if not pairs:
            return []

        lines: list[str] = []
        for field, group in pairs[:FETCH_KEY_DIAGNOSTIC_LIMIT]:
            lines.extend(self._one_diagnostic(field, group))

        return lines

    @staticmethod
    def _one_diagnostic(field: str, group: str) -> list[str]:
        """One DISPLAY, wrapped as many times as the window demands.

        REGRESSION - the two-line form was not always enough

        IND_WHEN_BODY(11) + "DISPLAY '"(9) + label(18) + "' : ' "(5)
        costs 43 columns, leaving 22 for the operand. A COBOL data-name
        may be 30 characters, so even the field ALONE can overflow:

            DISPLAY 'DA-VERYLONGCOLUMNN : ' DA-VERYLONGCOLUMNNAME-479BFAS
                                                                        ^ col 79

        Escalation, in order:
            1. literal + field + OF group      on one line
            2. literal + field / OF group      on two lines
            3. literal / field / OF group      on three lines
            4. none of the above fits          -> emit nothing

        Step 4 is deliberate. A truncated data-name does not compile;
        losing one diagnostic line does no harm.
        """
        label = field[:FETCH_KEY_LABEL_WIDTH].ljust(FETCH_KEY_LABEL_WIDTH)
        qualified = FETCH_KEY_HOST_TEMPLATE.format(field=field, group=group)

        # 1. one line
        single = IND_WHEN_BODY + FETCH_KEY_DISPLAY_TEMPLATE.format(
            label=label,
            host=qualified,
        )
        if CursorParagraphBodyBuilder._fits(single):
            return [single]

        of_group = CursorParagraphBodyBuilder._continuation(f"OF {group}")
        if not of_group:
            return []

        # 2. literal + field, then OF group
        head = IND_WHEN_BODY + FETCH_KEY_DISPLAY_TEMPLATE.format(
            label=label,
            host=field,
        )
        if CursorParagraphBodyBuilder._fits(head):
            return [head, of_group]

        # 3. literal alone, then field, then OF group
        literal = (
            IND_WHEN_BODY
            + FETCH_KEY_DISPLAY_TEMPLATE.format(label=label, host="").rstrip()
        )
        field_line = CursorParagraphBodyBuilder._continuation(field)

        if CursorParagraphBodyBuilder._fits(literal) and field_line:
            return [literal, field_line, of_group]

        # 4. cannot be represented - skip rather than corrupt the source
        return []

    @staticmethod
    def _fits(line: str) -> bool:
        """True when the body line ends on or before the window edge.

        Body starts at column 8, so the physical end column of a body
        of length n is 7 + n.
        """
        return 7 + len(str(line or "")) <= FETCH_KEY_BODY_END_COLUMN

    @staticmethod
    def _continuation(text: str) -> str:
        """A continuation fragment at the widest indent that still fits.

        Prefers IND_WHEN_BODY_CONT, which aligns under the DISPLAY
        operands the way the manual reference lays them out, and falls
        back to IND_WHEN_BODY when the fragment is too wide for it.
        Returns "" when neither works, which makes the caller skip the
        whole diagnostic rather than emit an over-long line.
        """
        body = str(text or "").strip()
        if not body:
            return ""

        for indent in (IND_WHEN_BODY_CONT, IND_WHEN_BODY):
            candidate = f"{indent}{body}"
            if CursorParagraphBodyBuilder._fits(candidate):
                return candidate

        return ""
    
    @staticmethod
    def _host_pairs(host_variables: list[str] | None) -> list[tuple[str, str]]:
        """(field, group) for every QUALIFIED host in the INTO list.

        Accepts the same three forms _host_group() accepts, because the
        resolver may deliver any of them:

            :DCLDZBFASTV.DA-CPTAFS-479BFAS
            DCLDZBFASTV.DA-CPTAFS-479BFAS
            DA-CPTAFS-479BFAS OF DCLDZBFASTV

        An unqualified host is SKIPPED, never guessed at.
        """
        output: list[tuple[str, str]] = []

        for host in host_variables or []:
            text = str(host or "").strip().lstrip(":").strip()
            if not text:
                continue

            upper = text.upper()
            if " OF " in upper:
                cut = upper.rindex(" OF ")
                field = text[:cut].strip()
                group = text[cut + 4:].strip()
            elif "." in text:
                group, _, field = text.partition(".")
                group = group.strip()
                field = field.strip()
            else:
                continue

            if field and group:
                output.append((field.upper(), group.upper()))

        return output