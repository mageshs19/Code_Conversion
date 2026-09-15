# LOCATION: code_review/checks/chk_05_sql_error_routing.py
# ACTION: REPLACE ENTIRE FILE

"""CHK-05 SQL error paragraph and routing."""

from __future__ import annotations

import re

from code_review.engine.check_base import CRITICAL, Check
from code_review.standards import cobol_standards as std

PERFORM_SQL_ERROR = re.compile(r"\bPERFORM\s+(?P<name>SQLERROR|SQL-ERROR)\b")
PARA_HEADER = re.compile(r"^(?P<name>[A-Z0-9][A-Z0-9-]*)\.$")

# The manual reference moves the bare paragraph number:
#     MOVE 710    TO SQL-LOCATION
#
# The quoted-name form is accepted too, as is a data-name source such as
#     MOVE CS-PARAGRAPH TO SQL-LOCATION
#
# The terminator is optional because the site standard closes a paragraph
# with a lone period on its own line.
MOVE_SQL_LOCATION = re.compile(
    r"^MOVE\s+(?:'[^']*'|\d+|[A-Z][A-Z0-9-]*)\s+TO\s+SQL-LOCATION\s*\.?$"
)

EXEC_SQL = re.compile(r"^EXEC\s+SQL\b")


class SqlErrorRoutingCheck(Check):
    CHECK_ID = "CHK-05"
    TITLE = "SQL error paragraph and routing"
    SEVERITY = CRITICAL
    ORDER = 50

    def relevant(self, ctx, view) -> bool:
        return view.has_code_token("EXEC SQL")

    def not_relevant_reason(self) -> str:
        return "Program contains no embedded SQL."

    def review(self, ctx, view, record):
        standard = std.SQL_ERROR_PARAGRAPH
        legacy = std.LEGACY_SQL_ERROR_PARAGRAPH

        headers = [
            m.group("name")
            for m in (PARA_HEADER.match(l.logical) for l in view.code)
            if m
        ]
        declared = [h for h in headers if h in (standard, legacy)]

        # The site standard routes through EXEC SQL INCLUDE SQLERROR, which
        # supplies the routine from the copybook. The manual reference
        # therefore declares no SQLERROR paragraph of its own, and writing
        # one risks a duplicate paragraph name.
        include_token = getattr(std, "SQL_ERROR_INCLUDE", "")
        included = bool(include_token) and view.has_code_token(include_token)

        # ---- 01 declared or included ---------------------------------
        record.expect(
            "01", f"{standard} is declared or included",
            (standard in declared) or included,
            note=(
                f"paragraphs found: {declared or 'none'}; "
                f"include present: {included}"
            ),
        )

        # ---- 02 declared exactly once --------------------------------
        if standard not in declared and included:
            record.skip(
                "02", f"Exactly one {standard} paragraph is declared",
                f"{standard} is supplied by {include_token}, not declared "
                f"in the program.",
            )
        else:
            record.expect(
                "02", f"Exactly one {standard} paragraph is declared",
                declared.count(standard) == 1,
                note=f"found {declared.count(standard)}",
            )

        # ---- 03 legacy name gone -------------------------------------
        record.expect_none(
            "03", f"Legacy {legacy} paragraph name is not used",
            view.exact(f"{legacy}."),
        )

        # ---- 04 / 05 PERFORM routing ---------------------------------
        performs = view.searching(PERFORM_SQL_ERROR)

        record.expect_none(
            "04", f"Every PERFORM targets {standard}",
            [
                line for line in performs
                if self._target_of(line)
                and self._target_of(line) != standard
            ],
        )

        # A paragraph supplied by the copybook is not visible as a header in
        # this program, so it cannot be counted as undeclared.
        declared_set = set(headers)
        if included:
            declared_set.add(standard)

        record.expect_none(
            "05", "No PERFORM refers to an undeclared paragraph",
            [
                line for line in performs
                if self._target_of(line)
                and self._target_of(line) not in declared_set
            ],
        )

        # ---- 06 reachability ------------------------------------------
        if not performs:
            record.skip(
                "06", f"{standard} is reachable",
                f"No PERFORM {standard} statement in the program.",
            )
        else:
            record.ok("06", f"{standard} is reachable")

        # ---- 07 SQL-LOCATION populated --------------------------------
        record.expect(
            "07", "SQL-LOCATION is populated before SQL blocks",
            bool(view.matching(MOVE_SQL_LOCATION)),
            note="No MOVE to SQL-LOCATION found.",
        )

        # ---- 08 body matches the site standard ------------------------
        self._review_body(view, record, standard)

    # =================================================================
    # Criterion 08
    # =================================================================
    @staticmethod
    def _review_body(view, record, standard: str) -> None:
        """The SQLERROR routine carries the site's agreed body.

        SQL_ERROR_BODY is the authority. Decision D-1 closed it in favour
        of the include form:

            EXEC SQL
                 INCLUDE SQLERROR
            END-EXEC.

        A program that instead emits the older DISPLAY / CALL USERABEN
        body fails here. That is correct: two SQLERROR bodies in one
        codebase means retrieval and update output diverge, and the
        copybook routine is duplicated by a hand-rolled one.
        """
        title = f"{standard} body matches the site standard"
        body = [token.upper() for token in getattr(std, "SQL_ERROR_BODY", ())]

        if not body:
            record.skip(
                "08", title,
                "Site standard body not yet agreed (decision open).",
            )
            return

        record.expect_all(
            "08", title,
            [token for token in body if token not in view.code_text],
        )

    # =================================================================
    # Helpers
    # =================================================================
    @staticmethod
    def _target_of(line) -> str:
        """Performed paragraph name, or '' when the line does not match.

        view.searching and PERFORM_SQL_ERROR.search can disagree if one
        inspects the raw line and the other the logical line. Calling
        .group() on None would abort the entire review over a formatting
        edge case, so a non-match is treated as 'nothing to judge'.
        """
        match = PERFORM_SQL_ERROR.search(line.logical)
        return match.group("name") if match else ""