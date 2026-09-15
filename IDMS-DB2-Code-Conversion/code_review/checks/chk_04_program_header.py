"""CHK-04 Compiler option and PROGRAM-ID."""

from __future__ import annotations

import re

from code_review.engine.check_base import CRITICAL, Check
from code_review.standards import cobol_standards as std

CBL = re.compile(r"^CBL\b.*$")
PROG = re.compile(r"^PROGRAM-ID\.\s*(?P<name>[A-Z0-9-]+)\s*\.?$")
ENDP = re.compile(r"^END\s+PROGRAM\s+(?P<name>[A-Z0-9-]+)\s*\.?$")

# The level number is CAPTURED, not hardcoded, so CS_PROGRAM_LEVELS governs
# it and decision D-2 can be settled from standards/ alone. The manual
# reference declares CS-PROGRAM as a 10-level inside 01 WS-TE-WORK.
#
# NOTE: the previous pattern read "PIC\s+X$8$", where $ is an end-of-string
# anchor, not a literal parenthesis. It could never match, which is why
# criterion 06 always skipped with "CS-PROGRAM not declared".
CSPG = re.compile(
    r"^(?P<level>\d{2})\s+CS-PROGRAM\s+"
    r"PIC\s+X\s*$\s*8\s*$\s+"
    r"VALUE\s+['\"]\s*(?P<v>[A-Z0-9-]*?)\s*['\"]\s*\.?\s*$",
    flags=re.IGNORECASE,
)

SITE = re.compile(r"^(VM)([A-Z0-9]?)(BD)([A-Z0-9]+)$")


def derive(name: str) -> str:
    text = str(name or "").strip().upper()
    m = SITE.match(text)
    return f"{std.NAME_PREFIX}{std.NAME_TARGET_MARKER}{m.group(2)}{m.group(4)}" if m else text


class ProgramHeaderCheck(Check):
    CHECK_ID = "CHK-04"
    TITLE = "Compiler option and PROGRAM-ID"
    SEVERITY = CRITICAL
    ORDER = 40

    def review(self, ctx, view, record):
        options = [l for l in view.code if CBL.match(l.logical)]
        record.expect(
            "01", f"Compiler option is {std.COMPILER_OPTION_LINE}",
            bool(options) and options[0].logical == std.COMPILER_OPTION_LINE.upper(),
            note=f"found '{options[0].logical}'" if options else "no CBL line found",
            findings=options[:1],
        )
        record.expect("02", "Exactly one compiler option line", len(options) == 1,
                      note=f"found {len(options)}")

        actual = view.first_group(PROG, "name")
        record.expect("03", "PROGRAM-ID is present", bool(actual))

        expected = ctx.target_program_id.upper() or (
            derive(ProgramHeaderCheck._source_id(ctx)) if ctx.source_cobol else ""
        )
        if expected:
            record.expect("04", f"PROGRAM-ID is {expected}", actual == expected,
                          note=f"found '{actual}'")
        else:
            record.skip("04", "PROGRAM-ID matches derived name",
                        "No source program supplied for comparison.")

        # ---- 05 END PROGRAM
        #
        # The manual reference program emits no END PROGRAM statement, so this
        # is gated rather than always scored. See ENFORCE_END_PROGRAM.
        if not getattr(std, "ENFORCE_END_PROGRAM", True):
            record.skip("05", "END PROGRAM matches PROGRAM-ID",
                        "END PROGRAM is not part of the site standard.")
        else:
            end_name = view.first_group(ENDP, "name")
            if end_name:
                record.expect("05", "END PROGRAM matches PROGRAM-ID",
                              end_name == actual,
                              note=f"END PROGRAM '{end_name}' vs '{actual}'")
            else:
                record.skip("05", "END PROGRAM matches PROGRAM-ID",
                            "No END PROGRAM statement.")

        # ---- 06 CS-PROGRAM holds the PROGRAM-ID
        levels = getattr(std, "CS_PROGRAM_LEVELS", ("01", "77"))
        field = getattr(std, "CS_PROGRAM_FIELD", "CS-PROGRAM")

        matches = [
            m
            for m in (CSPG.match(l.logical) for l in view.code)
            if m and m.group("level") in levels
        ]

        if not matches:
            record.skip(
                "06", f"{field} holds the PROGRAM-ID",
                f"{field} not declared at level {', '.join(levels)}.",
            )
        else:
            values = [m.group("v").strip().upper() for m in matches]
            wanted = str(actual or "").strip().upper()
            record.expect(
                "06", f"{field} holds the PROGRAM-ID",
                all(v == wanted for v in values),
                note=f"PROGRAM-ID '{actual}', {field} {values}",
            )

    @staticmethod
    def _source_id(ctx) -> str:
        for raw in str(ctx.source_cobol or "").splitlines():
            body = raw[7:72] if len(raw) >= 80 else raw
            m = PROG.match(body.strip().upper())
            if m:
                return m.group("name")
        return ""