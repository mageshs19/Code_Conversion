"""CHK-25 Copybook and record usage validation."""

from __future__ import annotations

import re

from code_review.engine import metadata as meta, sql_blocks as sql
from code_review.engine.check_base import MAJOR, Check
from code_review.standards import cobol_standards as std

QUALIFIED = re.compile(
    r"\b(?P<field>[A-Z][A-Z0-9-]*)\s+(?:OF|IN)\s+(?P<group>[A-Z][A-Z0-9-]*)\b"
)
COPY = re.compile(r"^COPY\s+(?P<name>[A-Z0-9][A-Z0-9_-]*)\b")
DATA_ITEM = re.compile(
    r"^(?P<level>0[1-9]|[1-4][0-9]|66|77|88)\s+(?P<name>[A-Z][A-Z0-9-]*)\b"
)
LITERAL = re.compile(r"'[^']*'|\"[^\"]*\"")


def without_literals(text: str) -> str:
    """Blank out quoted literals.

    COBOL qualification only applies to identifiers. Display text such as
    DISPLAY 'DATE OF ERROR' is prose, not a field reference, and must not
    be parsed as one.
    """
    return LITERAL.sub(" ", str(text or ""))


class CopybookAndRecordUsageCheck(Check):
    CHECK_ID = "CHK-25"
    TITLE = "Copybook and record usage validation"
    SEVERITY = MAJOR
    ORDER = 250

    def relevant(self, ctx, view) -> bool:
        return bool(ctx.sheet_mapping_rows) or bool(ctx.copybook_fields)

    def not_relevant_reason(self) -> str:
        return "No Sheet Mapping or copybook metadata supplied for this run."

    def review(self, ctx, view, record):
        prefix = std.DCLGEN_GROUP_PREFIX.upper()
        records = meta.mapped_records(ctx)
        qualifiers = self._qualifiers(view)
        copies = self._copies(view)
        copybook = self._copybook_fields(ctx)
        declared = self._declared_names(view)

        # ---- 01 no IDMS record survives as a qualifier --------------
        if not std.ENFORCE_NO_IDMS_QUALIFIER:
            record.skip(
                "01", "No IDMS record name survives as a field qualifier",
                "Not enforced by the site standard.",
            )
        elif not records:
            record.skip(
                "01", "No IDMS record name survives as a field qualifier",
                "No Sheet Mapping record metadata supplied for this run.",
            )
        else:
            record.expect_all(
                "01", "No IDMS record name survives as a field qualifier",
                sorted({
                    f"{field} OF {group}"
                    for field, group in qualifiers
                    if group in records
                }),
            )

        # ---- 02 every qualifier resolves to a declared group --------
        if not qualifiers:
            record.skip(
                "02",
                "Every qualified reference resolves to a declared group",
                "Program contains no qualified field reference.",
            )
        else:
            known = (
                {f"{prefix}{table}" for table in meta.dclgen_tables(ctx)}
                | copybook
                | set(copies)
                | declared
            )
            record.expect_all(
                "02",
                "Every qualified reference resolves to a declared group",
                sorted({
                    f"{field} OF {group}"
                    for field, group in qualifiers
                    if group not in known
                }),
            )

        # ---- 03 every mapped record is converted or documented ------
        if not records:
            record.skip(
                "03",
                "Every referenced IDMS record was converted or documented",
                "No Sheet Mapping record metadata supplied for this run.",
            )
        elif not ctx.has_source:
            record.skip(
                "03",
                "Every referenced IDMS record was converted or documented",
                "No source program supplied for comparison.",
            )
        else:
            record.expect_all(
                "03",
                "Every referenced IDMS record was converted or documented",
                self._undocumented(ctx, view, records),
            )

        # ---- 04 no unmapped record marker remains -------------------
        record.expect_none(
            "04", "No unmapped business record marker remains",
            [
                line for line in view.comments
                if any(m in line.logical for m in std.MISSING_MAPPING_MARKERS)
                and not any(
                    hint in line.logical
                    for hint in std.RESTART_CONTROL_HINTS
                )
            ],
        )

        # ---- 05 copybook-qualified fields exist ---------------------
        if not copybook:
            record.skip(
                "05", "Every copybook-qualified field exists in the copybook",
                "No copybook metadata supplied for this run.",
            )
        elif not qualifiers:
            record.skip(
                "05", "Every copybook-qualified field exists in the copybook",
                "Program contains no qualified field reference.",
            )
        else:
            record.expect_all(
                "05", "Every copybook-qualified field exists in the copybook",
                sorted({
                    f"{field} OF {group}"
                    for field, group in qualifiers
                    if group in copybook
                    and not group.startswith(prefix)
                    and field not in copybook
                    and field not in declared
                }),
            )

        # ---- 06 every COPY member is referenced ---------------------
        if not copies:
            record.skip(
                "06", "Every COPY member is referenced",
                "Program declares no COPY statement.",
            )
        else:
            referenced = {group for _field, group in qualifiers}
            record.expect_all(
                "06", "Every COPY member is referenced",
                sorted(
                    name for name in copies
                    if name not in referenced
                    and not view.has_code_token(name)
                ),
            )

    # ---- helpers ----------------------------------------------------
    @staticmethod
    def _qualifiers(view) -> set[tuple[str, str]]:
        out: set[tuple[str, str]] = set()
        for line in view.code:
            body = without_literals(sql.norm(line.logical))
            for match in QUALIFIED.finditer(body):
                out.add((match.group("field"), match.group("group")))
        return out

    @staticmethod
    def _copies(view) -> set[str]:
        out: set[str] = set()
        for line in view.code:
            match = COPY.match(sql.norm(line.logical))
            if match:
                out.add(match.group("name"))
        return out

    @staticmethod
    def _copybook_fields(ctx) -> set[str]:
        return {
            meta.field(item, "name")
            for item in (ctx.copybook_fields or [])
            if meta.field(item, "name")
        }

    @staticmethod
    def _declared_names(view) -> set[str]:
        """Every data name the program declares in its own DATA DIVISION."""
        out: set[str] = set()
        for line in view.code:
            match = DATA_ITEM.match(sql.norm(line.logical))
            if match:
                out.add(match.group("name"))
        return out

    @staticmethod
    def _table_variants(table: str) -> set[str]:
        """Every equivalent DB2 table spelling, TB and TV included."""
        text = str(table or "").strip().upper()
        if not text:
            return set()
        out = {text}
        for source, target in std.DB2_TABLE_SUFFIX_EQUIVALENTS:
            if text.endswith(source):
                out.add(f"{text[: -len(source)]}{target}")
        return out

    @classmethod
    def _undocumented(cls, ctx, view, records: set[str]) -> list[str]:
        source = sql.norm(ctx.source_cobol)
        comments = " ".join(line.logical for line in view.comments)

        out: list[str] = []
        for name in sorted(name for name in records if name in source):
            table = meta.table_for_record(ctx, name)
            if any(
                view.has_code_token(item)
                for item in cls._table_variants(table)
            ):
                continue
            if name in comments:
                continue
            out.append(f"{name} (table {table or 'unmapped'})")
        return out