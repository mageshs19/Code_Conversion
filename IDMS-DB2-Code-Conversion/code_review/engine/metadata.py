"""Read-only classification of the metadata carried on a ReviewContext.

Sheet Mapping is the authority for DB2 table and column names.
DCLGEN is the authority for host variable spelling and picture clauses.

Every function tolerates missing metadata by returning an empty result, so
callers can skip a criterion rather than fail it. Prefix tuples are passed
in by the caller, keeping this module free of site standards.
"""

from __future__ import annotations

import re

WS_RUN = re.compile(r"\s+")
KEY_FOREIGN = "FOREIGN"
KEY_FK = " FK "


def norm_name(value) -> str:
    """Uppercase, trimmed, whitespace collapsed."""
    return WS_RUN.sub(" ", str(value or "").strip().upper())


def field(row, *names, default: str = "") -> str:
    """First populated attribute from a metadata row."""
    for name in names:
        value = norm_name(getattr(row, name, ""))
        if value:
            return value
    return default


# ---- DCLGEN ----------------------------------------------------------
def dclgen_tables(ctx) -> set[str]:
    return {
        field(column, "table_name")
        for column in (ctx.dclgen_columns or [])
        if field(column, "table_name")
    }


def columns_for_table(ctx, table: str) -> set[str]:
    wanted = norm_name(table)
    return {
        field(column, "column_name")
        for column in (ctx.dclgen_columns or [])
        if field(column, "table_name") == wanted
        and field(column, "column_name")
    }


def hosts_for_table(ctx, table: str) -> dict[str, str]:
    """DB2 column -> COBOL host variable, for one table."""
    wanted = norm_name(table)
    out: dict[str, str] = {}
    for column in ctx.dclgen_columns or []:
        if field(column, "table_name") != wanted:
            continue
        name = field(column, "column_name")
        host = field(column, "cobol_host_name")
        if name and host:
            out[name] = host
    return out


def columns_with_prefix(ctx, table: str, prefixes) -> set[str]:
    """DCLGEN columns of a table whose name starts with any prefix."""
    wanted = tuple(norm_name(p) for p in (prefixes or ()) if norm_name(p))
    if not wanted:
        return set()
    return {
        name for name in columns_for_table(ctx, table)
        if name.startswith(wanted)
    }


def picture_for(ctx, table: str, column: str) -> str:
    wanted_table = norm_name(table)
    wanted_column = norm_name(column)
    for item in ctx.dclgen_columns or []:
        if field(item, "table_name") != wanted_table:
            continue
        if field(item, "column_name") != wanted_column:
            continue
        return field(item, "cobol_picture")
    return ""


# ---- Sheet Mapping ---------------------------------------------------
def rows_for_record(ctx, record: str) -> list:
    wanted = norm_name(record)
    return [
        row for row in (ctx.sheet_mapping_rows or [])
        if field(row, "cobol_record_idms") == wanted
    ]


def mapped_records(ctx) -> set[str]:
    return {
        field(row, "cobol_record_idms")
        for row in (ctx.sheet_mapping_rows or [])
        if field(row, "cobol_record_idms")
    }


def table_for_record(ctx, record: str) -> str:
    for row in rows_for_record(ctx, record):
        table = field(row, "new_db2_record", "cross_application_db2_table")
        if table:
            return table
    return ""


def mapped_tables(ctx) -> set[str]:
    return {
        field(row, "new_db2_record", "cross_application_db2_table")
        for row in (ctx.sheet_mapping_rows or [])
        if field(row, "new_db2_record", "cross_application_db2_table")
    }


def mapped_columns(ctx) -> set[str]:
    return {
        field(row, "new_db2_field_name", "cross_application_db2_field_name")
        for row in (ctx.sheet_mapping_rows or [])
        if field(row, "new_db2_field_name", "cross_application_db2_field_name")
    }


def _column_of(row) -> str:
    return field(
        row, "new_db2_field_name", "cross_application_db2_field_name",
    )


def _is_foreign(row) -> bool:
    text = " ".join([field(row, "db2_key"), field(row, "relation")])
    return KEY_FOREIGN in text or KEY_FK in f" {text} "


def primary_key_columns(ctx, record: str, key_markers) -> list[str]:
    """Composite PK and CALC key columns. FOREIGN columns are excluded."""
    markers = tuple(norm_name(m) for m in (key_markers or ()) if norm_name(m))
    out: list[str] = []
    seen: set[str] = set()

    for row in rows_for_record(ctx, record):
        column = _column_of(row)
        if not column or column in seen:
            continue
        if _is_foreign(row):
            continue
        text = " ".join([field(row, "idms_key"), field(row, "db2_key")])
        if not any(marker in text for marker in markers):
            continue
        seen.add(column)
        out.append(column)
    return out


def foreign_key_columns(ctx, record: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for row in rows_for_record(ctx, record):
        if not _is_foreign(row):
            continue
        column = _column_of(row)
        if column and column not in seen:
            seen.add(column)
            out.append(column)
    return out


def all_primary_key_columns(ctx, key_markers) -> set[str]:
    out: set[str] = set()
    for record in mapped_records(ctx):
        out.update(primary_key_columns(ctx, record, key_markers))
    return out


def all_foreign_key_columns(ctx) -> set[str]:
    out: set[str] = set()
    for record in mapped_records(ctx):
        out.update(foreign_key_columns(ctx, record))
    return out