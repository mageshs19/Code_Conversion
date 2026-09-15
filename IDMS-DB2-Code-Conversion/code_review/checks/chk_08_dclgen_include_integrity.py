"""CHK-08 DCLGEN include and copybook integrity."""

from __future__ import annotations

import re
from collections import Counter

from code_review.engine.check_base import CRITICAL, Check
from code_review.standards import cobol_standards as std

INCLUDE = re.compile(
    r"^EXEC\s+SQL\s+INCLUDE\s+(?P<name>[A-Z0-9][A-Z0-9_-]*)\s+END-EXEC\s*\.?$"
)
COPY = re.compile(r"^COPY\s+(?P<name>[A-Z0-9][A-Z0-9_-]*)\b")
WS_SECTION = re.compile(r"^WORKING-STORAGE\s+SECTION\s*\.?$")
PROCEDURE_DIVISION = re.compile(r"^PROCEDURE\s+DIVISION\b")
WS_RUN = re.compile(r"\s+")


def norm(text: str) -> str:
    """Uppercase, trimmed, internal whitespace runs collapsed."""
    return WS_RUN.sub(" ", str(text or "").strip().upper())


def statements(lines: list[str]) -> list[str]:
    """Logical statements, with EXEC SQL ... END-EXEC. joined into one entry.

    Order is preserved, so positional criteria remain valid.
    """
    out: list[str] = []
    buffer: list[str] = []
    inside = False

    for raw in lines:
        line = norm(raw)

        if not inside and line.startswith(std.SQL_BLOCK_START):
            inside = True
            buffer = [line]
            if std.SQL_BLOCK_END in line:
                out.append(" ".join(buffer))
                inside, buffer = False, []
            continue

        if inside:
            buffer.append(line)
            if std.SQL_BLOCK_END in line:
                out.append(" ".join(buffer))
                inside, buffer = False, []
            continue

        out.append(line)

    if buffer:
        out.append(" ".join(buffer))
    return out


def is_infrastructure(name: str) -> bool:
    """SQLCA, SQLERRWS, SQLERROR and GEN are not DCLGEN table includes."""
    return str(name or "").strip().upper() in std.EXCLUDED_INCLUDE_NAMES


class DclgenIncludeIntegrityCheck(Check):
    CHECK_ID = "CHK-08"
    TITLE = "DCLGEN include and copybook integrity"
    SEVERITY = CRITICAL
    ORDER = 80

    def relevant(self, ctx, view) -> bool:
        return view.has_code_token(std.SQL_BLOCK_START)

    def not_relevant_reason(self) -> str:
        return "Program contains no embedded SQL."

    def review(self, ctx, view, record):
        code = statements([line.logical for line in view.code])

        included = [
            INCLUDE.match(line).group("name").upper()
            for line in code
            if INCLUDE.match(line)
        ]
        dclgen_includes = [
            name for name in included if not is_infrastructure(name)
        ]
        include_set = set(dclgen_includes)

        groups = self._referenced_groups(view)
        referenced_tables = {self._table_of(group) for group in groups}

        copies = [
            COPY.match(line).group("name").upper()
            for line in code
            if COPY.match(line)
        ]

        # ---- 01 no DCLGEN include is unused -------------------------
        if not dclgen_includes:
            record.skip(
                "01", "Every DCLGEN include is actually used",
                "Program declares no DCLGEN include.",
            )
        else:
            record.expect_all(
                "01", "Every DCLGEN include is actually used",
                sorted(
                    name for name in include_set
                    if name not in referenced_tables
                ),
            )

        # ---- 02 each include declared exactly once ------------------
        duplicates = [
            f"{name} x{count}"
            for name, count in sorted(Counter(included).items())
            if count > 1
        ]
        record.expect_all(
            "02", "Each INCLUDE is declared exactly once", duplicates,
            note=f"{len(duplicates)} duplicated include(s)" if duplicates else "",
        )

        # ---- 03 DCLGEN includes sit inside WORKING-STORAGE ----------
        #
        # Only DCLGEN table includes are placement-checked. Infrastructure
        # includes are exempt on purpose: the converter emits
        # "EXEC SQL INCLUDE SQLERROR END-EXEC." inside the PROCEDURE
        # DIVISION SQLERROR paragraph, which is correct.
        if not std.ENFORCE_INCLUDE_IN_WORKING_STORAGE:
            record.skip(
                "03", "DCLGEN INCLUDE statements sit inside WORKING-STORAGE",
                "Placement not enforced by the site standard.",
            )
        elif not dclgen_includes:
            record.skip(
                "03", "DCLGEN INCLUDE statements sit inside WORKING-STORAGE",
                "Program declares no DCLGEN include.",
            )
        else:
            ws_at = next(
                (i for i, line in enumerate(code) if WS_SECTION.match(line)),
                -1,
            )
            pd_at = next(
                (
                    i for i, line in enumerate(code)
                    if PROCEDURE_DIVISION.match(line)
                ),
                -1,
            )
            if ws_at < 0 or pd_at < 0:
                record.skip(
                    "03",
                    "DCLGEN INCLUDE statements sit inside WORKING-STORAGE",
                    "Section markers not found.",
                )
            else:
                late = []
                for index, line in enumerate(code):
                    match = INCLUDE.match(line)
                    if not match:
                        continue
                    if is_infrastructure(match.group("name")):
                        continue
                    if not (ws_at < index < pd_at):
                        late.append(line)
                record.expect_all(
                    "03",
                    "DCLGEN INCLUDE statements sit inside WORKING-STORAGE",
                    late,
                )

        # ---- 04 every referenced DCL group has an include -----------
        if not groups:
            record.skip(
                "04",
                f"Every referenced {std.DCLGEN_GROUP_PREFIX} group has an "
                f"INCLUDE",
                "No DCLGEN host group referenced.",
            )
        else:
            record.expect_all(
                "04",
                f"Every referenced {std.DCLGEN_GROUP_PREFIX} group has an "
                f"INCLUDE",
                sorted(
                    group for group in groups
                    if self._table_of(group) not in include_set
                ),
            )

        # ---- 05 include names are real DCLGEN tables ----------------
        tables = self._dclgen_tables(ctx)
        if not tables:
            record.skip(
                "05", "Every INCLUDE names a known DCLGEN table",
                "No DCLGEN metadata supplied for this run.",
            )
        elif not dclgen_includes:
            record.skip(
                "05", "Every INCLUDE names a known DCLGEN table",
                "Program declares no DCLGEN include.",
            )
        else:
            record.expect_all(
                "05", "Every INCLUDE names a known DCLGEN table",
                sorted(name for name in include_set if name not in tables),
            )

        # ---- 06 host variables belong to an included table ----------
        hosts = self._dclgen_hosts(ctx)
        if not hosts:
            record.skip(
                "06", "Every DCLGEN host variable used has its table included",
                "No DCLGEN metadata supplied for this run.",
            )
        else:
            used_tables = {
                table for host, table in hosts.items()
                if view.has_code_token(host)
            }
            record.expect_all(
                "06", "Every DCLGEN host variable used has its table included",
                sorted(
                    table for table in used_tables
                    if table not in include_set
                ),
            )

        # ---- 07 no forbidden COPY remains ---------------------------
        record.expect_all(
            "07", "No forbidden COPY member remains",
            [
                name for name in copies
                if name.startswith(std.FORBIDDEN_COPY_PREFIXES)
            ],
        )

        # ---- 08 no COPY member is declared twice --------------------
        if not copies:
            record.skip(
                "08", "Each COPY member is declared exactly once",
                "Program declares no COPY statement.",
            )
        else:
            repeated = [
                f"{name} x{count}"
                for name, count in sorted(Counter(copies).items())
                if count > 1
            ]
            record.expect_all(
                "08", "Each COPY member is declared exactly once", repeated,
            )

        # ---- 09 COPY members resolve to a copybook record -----------
        #
        # The supplied copybook metadata is a flat list of FIELD names and
        # carries no member or include name, so a COPY member can only be
        # matched against 01-level record names. That equivalence is not
        # yet agreed. See open decision D-9.
        records_01 = self._copybook_records(ctx)
        if not std.ENFORCE_COPY_MEMBER_RESOLUTION:
            record.skip(
                "09", "Every COPY member resolves to a copybook record",
                "Copybook member names are not part of the supplied "
                "metadata (decision open).",
            )
        elif not records_01:
            record.skip(
                "09", "Every COPY member resolves to a copybook record",
                "No copybook 01-level record supplied for this run.",
            )
        elif not copies:
            record.skip(
                "09", "Every COPY member resolves to a copybook record",
                "Program declares no COPY statement.",
            )
        else:
            record.expect_all(
                "09", "Every COPY member resolves to a copybook record",
                sorted(
                    name for name in set(copies)
                    if name not in records_01
                ),
            )

    # ---- helpers ----------------------------------------------------
    @staticmethod
    def _table_of(group: str) -> str:
        """DCLDZBEFFTV -> DZBEFFTV."""
        text = str(group or "").strip().upper()
        prefix = std.DCLGEN_GROUP_PREFIX.upper()
        return text[len(prefix):] if text.startswith(prefix) else text

    @staticmethod
    def _referenced_groups(view) -> set[str]:
        prefix = std.DCLGEN_GROUP_PREFIX.upper()
        pattern = re.compile(rf"\b{prefix}[A-Z0-9_-]+\b")
        return set(pattern.findall(view.code_text))

    @staticmethod
    def _dclgen_tables(ctx) -> set[str]:
        return {
            str(getattr(column, "table_name", "") or "").strip().upper()
            for column in (ctx.dclgen_columns or [])
            if str(getattr(column, "table_name", "") or "").strip()
        }

    @staticmethod
    def _dclgen_hosts(ctx) -> dict[str, str]:
        out: dict[str, str] = {}
        for column in ctx.dclgen_columns or []:
            host = str(
                getattr(column, "cobol_host_name", "") or ""
            ).strip().upper()
            table = str(
                getattr(column, "table_name", "") or ""
            ).strip().upper()
            if host and table:
                out[host] = table
        return out

    @staticmethod
    def _copybook_records(ctx) -> set[str]:
        """01-level record names from the supplied copybook fields."""
        out: set[str] = set()
        for field in ctx.copybook_fields or []:
            level = str(getattr(field, "level", "") or "").strip()
            name = str(getattr(field, "name", "") or "").strip().upper()
            if name and level == std.COPYBOOK_RECORD_LEVEL:
                out.add(name)
        return out