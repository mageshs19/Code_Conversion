"""CHK-24 Picture clause and length validation."""

from __future__ import annotations

import re

from code_review.engine import metadata as meta
from code_review.engine.check_base import MAJOR, Check
from code_review.standards import cobol_standards as std

DIGITS = re.compile(r"^\d+$")
DB2_SIZED = re.compile(
    r"^(?P<type>[A-Z]+)\s*\(\s*(?P<size>\d+)", re.IGNORECASE
)

PIC_KEYWORDS = ("PICTURE", "PIC")
IS_KEYWORD = "IS"
LENGTH_SYMBOLS = "X9AZ"
IGNORED_SYMBOLS = "SV"

# DB2 types whose host length is fixed by the type itself.
FIXED_TYPE_LENGTHS = {
    "TIMESTAMP": 26,
    "DATE": 10,
    "TIME": 8,
}
CHARACTER_TYPES = ("CHAR", "CHARACTER", "GRAPHIC")


def _strip_picture_prefix(text: str) -> str:
    value = str(text or "").strip().upper()
    for keyword in PIC_KEYWORDS:
        if value.startswith(keyword):
            value = value[len(keyword):].strip()
            break
    if value.startswith(IS_KEYWORD):
        value = value[len(IS_KEYWORD):].strip()
    return value


def picture_length(picture: str) -> int:
    """Character length implied by a COBOL picture clause.

    Deliberately regex free. An explicit scan cannot silently drop a
    parenthesised repeat count, which is what makes PIC X(10) measure 1.

    S is a sign and V an implied decimal point, so neither occupies a
    stored position.
    """
    text = _strip_picture_prefix(picture).replace(" ", "").rstrip(".")
    if not text:
        return 0

    total = 0
    index = 0
    size = len(text)

    while index < size:
        symbol = text[index]

        if symbol in IGNORED_SYMBOLS:
            index += 1
            continue

        if symbol not in LENGTH_SYMBOLS:
            index += 1
            continue

        index += 1

        # Optional repeat count, for example X(10).
        if index < size and text[index] == "(":
            close = text.find(")", index)
            digits = text[index + 1:close] if close > index else ""
            if digits.isdigit():
                total += int(digits)
                index = close + 1
                continue

        total += 1

    return total


def picture_category(picture: str) -> str:
    """ALPHANUMERIC, NUMERIC or empty when undecidable."""
    text = _strip_picture_prefix(picture)
    if not text:
        return ""
    if "X" in text or "A" in text:
        return "ALPHANUMERIC"
    if "9" in text:
        return "NUMERIC"
    return ""


def db2_type_length(db2_type: str) -> int:
    """Host length implied by a DB2 type, 0 when not decidable.

    Fixed types are matched longest name first. TIMESTAMP starts with
    TIME, so insertion order would otherwise resolve a 26-character
    timestamp host to 8.
    """
    text = str(db2_type or "").strip().upper()
    if not text:
        return 0

    for name in sorted(FIXED_TYPE_LENGTHS, key=len, reverse=True):
        if text.startswith(name):
            return FIXED_TYPE_LENGTHS[name]

    match = DB2_SIZED.match(text)
    if match and match.group("type").startswith(CHARACTER_TYPES):
        return int(match.group("size"))
    return 0


def is_varchar(db2_type: str) -> bool:
    """A group host whose pictures live on its 49-level children."""
    return str(db2_type or "").strip().upper().startswith(std.VARCHAR_TYPES)


def has_comparable_length(db2_type: str) -> bool:
    """True when stored bytes and picture positions mean the same thing."""
    return str(db2_type or "").strip().upper().startswith(
        std.COMPARABLE_LENGTH_TYPES
    )


class PictureAndLengthCheck(Check):
    CHECK_ID = "CHK-24"
    TITLE = "Picture clause and length validation"
    SEVERITY = MAJOR
    ORDER = 240

    def relevant(self, ctx, view) -> bool:
        return bool(ctx.dclgen_columns)

    def not_relevant_reason(self) -> str:
        return "No DCLGEN metadata supplied for this run."

    def review(self, ctx, view, record):
        columns = list(ctx.dclgen_columns or [])

        # ---- 01 every scalar column has a picture -------------------
        #
        # VARCHAR columns are exempt: the host is a group and groups
        # carry no PICTURE of their own.
        record.expect_all(
            "01", "Every scalar DCLGEN column declares a picture clause",
            sorted({
                f"{meta.field(c, 'table_name')}."
                f"{meta.field(c, 'column_name')}"
                for c in columns
                if not meta.field(c, "cobol_picture")
                and not is_varchar(meta.field(c, "db2_type"))
            }),
        )

        # ---- 02 every DCLGEN column has a host name -----------------
        record.expect_all(
            "02", "Every DCLGEN column declares a host variable",
            sorted({
                f"{meta.field(c, 'table_name')}."
                f"{meta.field(c, 'column_name')}"
                for c in columns
                if not meta.field(c, "cobol_host_name")
            }),
        )

        # ---- 03 picture clauses resolve to a length -----------------
        record.expect_all(
            "03", "Every picture clause resolves to a length",
            sorted({
                f"{meta.field(c, 'cobol_host_name')} "
                f"PIC {meta.field(c, 'cobol_picture')}"
                for c in columns
                if meta.field(c, "cobol_picture")
                and picture_length(meta.field(c, "cobol_picture")) == 0
            }),
        )

        # ---- 04 Sheet Mapping length agrees with DCLGEN -------------
        if not std.ENFORCE_PICTURE_LENGTH_MATCH:
            record.skip(
                "04", "Character column lengths agree between Sheet "
                      "Mapping and DCLGEN",
                "Not enforced by the site standard.",
            )
        elif not ctx.sheet_mapping_rows:
            record.skip(
                "04", "Character column lengths agree between Sheet "
                      "Mapping and DCLGEN",
                "No Sheet Mapping metadata supplied for this run.",
            )
        else:
            record.expect_all(
                "04", "Character column lengths agree between Sheet "
                      "Mapping and DCLGEN",
                self._length_mismatches(ctx),
            )

        # ---- 05 source picture agrees with DCLGEN picture -----------
        if not ctx.sheet_mapping_rows:
            record.skip(
                "05", "Source picture length agrees with the DCLGEN picture",
                "No Sheet Mapping metadata supplied for this run.",
            )
        else:
            record.expect_all(
                "05", "Source picture length agrees with the DCLGEN picture",
                self._source_picture_mismatches(ctx),
            )

        # ---- 06 category agreement ----------------------------------
        if not ctx.sheet_mapping_rows:
            record.skip(
                "06", "Source and DB2 field categories agree",
                "No Sheet Mapping metadata supplied for this run.",
            )
        else:
            record.expect_all(
                "06", "Source and DB2 field categories agree",
                self._category_mismatches(ctx),
            )

        # ---- 07 host variables used declare a picture ---------------
        used = [
            column for column in columns
            if meta.field(column, "cobol_host_name")
            and view.has_code_token(meta.field(column, "cobol_host_name"))
            and not is_varchar(meta.field(column, "db2_type"))
        ]
        if not used:
            record.skip(
                "07", "Every scalar host variable used declares a picture",
                "No scalar DCLGEN host variable referenced in the program.",
            )
        else:
            record.expect_all(
                "07", "Every scalar host variable used declares a picture",
                sorted({
                    meta.field(column, "cobol_host_name")
                    for column in used
                    if not meta.field(column, "cobol_picture")
                }),
            )

        # ---- 08 picture agrees with its own DB2 type ----------------
        #
        # DCLGEN compared against DCLGEN, so a disagreement can only mean
        # the picture was parsed incorrectly.
        if not any(meta.field(c, "db2_type") for c in columns):
            record.skip(
                "08", "Every DCLGEN picture agrees with its DB2 type",
                "No DB2 type recorded in the supplied DCLGEN metadata.",
            )
        else:
            record.expect_all(
                "08", "Every DCLGEN picture agrees with its DB2 type",
                self._type_mismatches(ctx),
            )

    # ---- helpers ----------------------------------------------------
    @staticmethod
    def _target(row) -> tuple[str, str]:
        table = meta.field(
            row, "new_db2_record", "cross_application_db2_table",
        )
        column = meta.field(
            row, "new_db2_field_name", "cross_application_db2_field_name",
        )
        return table, column

    @staticmethod
    def _db2_type_for(ctx, table: str, column: str) -> str:
        wanted_table = meta.norm_name(table)
        wanted_column = meta.norm_name(column)
        for item in ctx.dclgen_columns or []:
            if meta.field(item, "table_name") != wanted_table:
                continue
            if meta.field(item, "column_name") != wanted_column:
                continue
            return meta.field(item, "db2_type")
        return ""

    @classmethod
    def _length_mismatches(cls, ctx) -> list[str]:
        """Compared only where bytes and positions mean the same thing."""
        out: list[str] = []
        for row in ctx.sheet_mapping_rows or []:
            table, column = cls._target(row)
            declared = meta.field(row, "length_of_field_bytes")
            if not table or not column or not DIGITS.match(declared):
                continue
            if not has_comparable_length(cls._db2_type_for(ctx, table, column)):
                continue
            actual = picture_length(meta.picture_for(ctx, table, column))
            if not actual:
                continue
            if abs(actual - int(declared)) > std.PICTURE_LENGTH_TOLERANCE:
                out.append(
                    f"{table}.{column}: Sheet Mapping {declared}, "
                    f"DCLGEN {actual}"
                )
        return sorted(set(out))

    @classmethod
    def _source_picture_mismatches(cls, ctx) -> list[str]:
        out: list[str] = []
        for row in ctx.sheet_mapping_rows or []:
            table, column = cls._target(row)
            if not table or not column:
                continue
            if not has_comparable_length(cls._db2_type_for(ctx, table, column)):
                continue
            source_pic = meta.field(
                row, "idms_pic_clause", "reference_field_pic_clause",
            )
            if not source_pic:
                continue
            source_length = picture_length(source_pic)
            target_length = picture_length(
                meta.picture_for(ctx, table, column)
            )
            if not source_length or not target_length:
                continue
            if abs(source_length - target_length) > (
                std.PICTURE_LENGTH_TOLERANCE
            ):
                out.append(
                    f"{table}.{column}: source {source_pic} "
                    f"({source_length}) vs DCLGEN ({target_length})"
                )
        return sorted(set(out))

    @classmethod
    def _category_mismatches(cls, ctx) -> list[str]:
        out: list[str] = []
        for row in ctx.sheet_mapping_rows or []:
            table, column = cls._target(row)
            if not table or not column:
                continue
            source_pic = meta.field(
                row, "idms_pic_clause", "reference_field_pic_clause",
            )
            source = picture_category(source_pic)
            target = picture_category(meta.picture_for(ctx, table, column))
            if not source or not target:
                continue
            if source != target:
                out.append(f"{table}.{column}: {source} to {target}")
        return sorted(set(out))

    @staticmethod
    def _type_mismatches(ctx) -> list[str]:
        out: list[str] = []
        for column in ctx.dclgen_columns or []:
            picture = meta.field(column, "cobol_picture")
            db2_type = meta.field(column, "db2_type")
            if not picture or not db2_type:
                continue
            if is_varchar(db2_type):
                continue
            expected = db2_type_length(db2_type)
            if not expected:
                continue
            actual = picture_length(picture)
            if not actual:
                continue
            if abs(actual - expected) > std.PICTURE_LENGTH_TOLERANCE:
                out.append(
                    f"{meta.field(column, 'table_name')}."
                    f"{meta.field(column, 'column_name')}: "
                    f"{db2_type} implies {expected}, "
                    f"PIC {picture} gives {actual}"
                )
        return sorted(set(out))