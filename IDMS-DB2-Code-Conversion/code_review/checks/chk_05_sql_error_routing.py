"""CHK-05 SQL error paragraph and routing."""

from __future__ import annotations

import re

from code_review.engine.check_base import CRITICAL, Check
from code_review.standards import cobol_standards as std

PERFORM_SQL_ERROR = re.compile(r"\bPERFORM\s+(?P<name>SQLERROR|SQL-ERROR)\b")
PARA_HEADER = re.compile(r"^(?P<name>[A-Z0-9][A-Z0-9-]*)\.$")

# The manual reference moves the bare paragraph number:
#     MOVE 710    TO SQL-LOCATION
# The quoted-name form is accepted too. The terminator is optional because
# the site standard closes a paragraph with a lone period line.
MOVE_SQL_LOCATION = re.compile(
    r"^MOVE\s+(?:'[^']*'|\d+)\s+TO\s+SQL-LOCATION\s*\.?$"
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

        record.expect(
            "01", f"{standard} is declared or included",
            (standard in declared) or included,
            note=(
                f"paragraphs found: {declared or 'none'}; "
                f"include present: {included}"
            ),
        )

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

        record.expect_none(
            "03", f"Legacy {legacy} paragraph name is not used",
            view.exact(f"{legacy}."),
        )

        performs = view.searching(PERFORM_SQL_ERROR)
        record.expect_none(
            "04", f"Every PERFORM targets {standard}",
            [l for l in performs
             if (PERFORM_SQL_ERROR.search(l.logical).group("name") != standard)],
        )

        # A paragraph supplied by the copybook is not visible as a header in
        # this program, so it cannot be counted as undeclared.
        declared_set = set(headers)
        if included:
            declared_set.add(standard)

        record.expect_none(
            "05", "No PERFORM refers to an undeclared paragraph",
            [l for l in performs
             if PERFORM_SQL_ERROR.search(l.logical).group("name") not in declared_set],
        )

        if not performs:
            record.skip("06", f"{standard} is reachable",
                        f"No PERFORM {standard} statement in the program.")
        else:
            record.ok("06", f"{standard} is reachable")

        record.expect(
            "07", "SQL-LOCATION is populated before SQL blocks",
            bool(view.matching(MOVE_SQL_LOCATION)),
            note="No MOVE to SQL-LOCATION found.",
        )

        body = [b.upper() for b in getattr(std, "SQL_ERROR_BODY", ())]
        if body:
            record.expect_all(
                "08", f"{standard} body matches the site standard",
                [b for b in body if b not in view.code_text],
            )
        else:
            record.skip("08", f"{standard} body matches the site standard",
                        "Site standard body not yet agreed (decision open).")