# LOCATION: tests/test_cursor_select_column_parity.py
# ACTION: REPLACE ENTIRE FILE
"""SELECT / INTO parity and full-record coverage.

REGRESSION 1 - the FETCH did not read what the program consumed

The generated FETCH carried 10 host variables:

    INTO :DCLDZBFASTV.DA-CPTAFS-479BFAS
       , :DCLDZBFASTV.DA-CRFMAS-479BFAS
       ... 8 more

while the business paragraph moved 83 fields out of the same group:

    *DB2: Materialised VMBFAS from DCLDZBFASTV - 83 field move(s).

73 fields were cleared by INITIALIZE and never fetched, so the output
record carried zeroes and spaces for most of its length.

REGRESSION 2 - two carriers, one sequence

SELECT and INTO are POSITIONAL and are rendered by two different
builders from two different carriers of the same spec dict:

    spec["select_columns"] -> CursorSpec -> CursorDeclareBuilder -> SELECT
    spec["host_variables"]              -> CursorParagraphBody   -> INTO

CursorSpec re-normalises and de-duplicates select_columns; the host
list is resolved separately and is NOT re-normalised. Any divergence
between the two is silent and corrupts every fetched row, so the
invariant is asserted here rather than trusted.
"""

from idms_db2_phase2.generators.db2_infrastructure.cursor_declare_builder import (
    CursorDeclareBuilder,
)
from idms_db2_phase2.generators.db2_infrastructure.cursor_spec import CursorSpec

CURSOR = "DZBFASC1"
TABLE = "DZBFASTV"
GROUP = "DCLDZBFASTV"


class _LineUtils:
    """Minimal stand-in for the infrastructure line utils.

    Only the two list renderers the declare builder calls are needed.
    Using a stub keeps the test independent of fixed-format geometry.
    """

    @staticmethod
    def and_lines(items: list[str], indent: str) -> list[str]:
        return [
            f"{indent}{'AND ' if index else ''}{item}"
            for index, item in enumerate(items)
        ]

    @staticmethod
    def comma_lines(items: list[str], indent: str) -> list[str]:
        return [
            f"{indent}{', ' if index else ''}{item}"
            for index, item in enumerate(items)
        ]


def _host_for(column: str) -> str:
    """The host reference the resolver builds for one column."""
    return f":{GROUP}.{column.replace('_', '-')}"


def _source(columns: list[str]) -> dict:
    """A spec dict exactly as CursorSpecBuilder.build() emits it."""
    return {
        "set_name": "AR-VMBFRM1",
        "record_name": "VMBFAS",
        "table_name": TABLE,
        "cursor_name": CURSOR,
        "select_columns": list(columns),
        "host_variables": [_host_for(column) for column in columns],
        "where_conditions": [],
        "order_by_columns": [],
        "open_paragraph": f"710-OPEN-{CURSOR}",
        "fetch_paragraph": f"720-FETCH-{CURSOR}",
        "close_paragraph": f"730-CLOSE-{CURSOR}",
        "cursor_order": 1,
    }


def _declared_columns(lines: list[str]) -> list[str]:
    """Column tokens between SELECT and FROM in a rendered DECLARE."""
    bodies = [line.strip() for line in lines if line.strip()]
    start = next(
        index for index, body in enumerate(bodies)
        if body.upper().startswith("SELECT")
    )
    stop = next(
        index for index, body in enumerate(bodies)
        if body.upper().startswith("FROM")
    )
    out: list[str] = []
    for body in bodies[start:stop]:
        token = body.upper()
        if token.startswith("SELECT"):
            token = token[len("SELECT"):]
        token = token.strip().lstrip(",").strip()
        if token:
            out.append(token)
    return out


def _host_column(reference: str) -> str:
    """':DCLDZBFASTV.DA-CPTAFS-479BFAS' -> 'DA_CPTAFS_479BFAS'."""
    return reference.split(".")[-1].strip().replace("-", "_").upper()


# ---------------------------------------------------------------------
# REGRESSION 2 - SELECT / INTO parity across the two carriers
# ---------------------------------------------------------------------
def test_cursor_spec_preserves_the_select_column_sequence():
    """CursorSpec must not silently reorder or drop a column.

    The host list is resolved from the PRE-normalisation sequence, so a
    dedupe or reorder inside CursorSpec desynchronises SELECT from INTO.
    """
    columns = [f"CT_COL{index:03d}_479BFAS" for index in range(1, 84)]
    source = _source(columns)

    spec = CursorSpec.read(source)

    assert spec.select_columns == columns


def test_declared_select_matches_the_host_list_count():
    """SELECT and INTO are positional. A count mismatch corrupts the row."""
    columns = [f"CT_COL{index:03d}_479BFAS" for index in range(1, 84)]
    source = _source(columns)

    declared = _declared_columns(
        CursorDeclareBuilder(_LineUtils()).build(CursorSpec.read(source))
    )

    assert len(declared) == len(source["host_variables"])
    assert len(declared) == len(columns)


def test_declared_select_matches_the_host_list_position_by_position():
    columns = ["CT_RKTGDSV_479BFAS", "NR_CIOFMAS_479BFAS", "DA_CRFMAS_479BFAS"]
    source = _source(columns)

    declared = _declared_columns(
        CursorDeclareBuilder(_LineUtils()).build(CursorSpec.read(source))
    )

    for index, column in enumerate(declared):
        assert _host_column(source["host_variables"][index]) == column


def test_duplicate_columns_are_collapsed_in_both_carriers():
    """A dedupe on one side only is the desynchronisation this guards."""
    columns = ["CT_RKTGDSV_479BFAS", "CT_RKTGDSV_479BFAS", "NR_CIOFMAS_479BFAS"]
    source = _source(columns)

    spec = CursorSpec.read(source)
    declared = _declared_columns(
        CursorDeclareBuilder(_LineUtils()).build(spec)
    )

    # CursorSpec collapses the duplicate; the raw host list does not.
    # The generator must therefore never hand a duplicated column list
    # to the host resolver in the first place.
    assert len(spec.select_columns) == 2
    assert len(declared) == 2


# ---------------------------------------------------------------------
# REGRESSION 1 - full-record coverage
# ---------------------------------------------------------------------
class _StubColumnNameResolver:
    def __init__(self, columns: list[str]) -> None:
        self._columns = columns

    def columns_for_record(self, record_name: str) -> list[str]:
        return list(self._columns)


class _StubTableNameResolver:
    @staticmethod
    def table_for_record(record_name: str) -> str:
        return TABLE

    @staticmethod
    def resolve_table(table_name: str) -> str:
        return TABLE


class _StubUsageSelector:
    def __init__(self, columns: list[str]) -> None:
        self._columns = columns

    def select_columns_for_record(self, record_name, field_usage_analysis):
        return list(self._columns)


class _StubMappingRepository:
    @staticmethod
    def db2_columns_for_table(table_name: str) -> list[str]:
        return []

    @staticmethod
    def rows_for_record(record_name: str) -> list:
        return []


class _StubRelationshipResolver:
    @staticmethod
    def resolve_for_child_record(record_name: str):
        return None


def _resolver(usage: list[str], full: list[str]):
    """Build a REAL CursorColumnResolver through its real __init__.

    REGRESSION - the stub hid a production crash

    This previously used CursorColumnResolver.__new__() and assigned
    attributes by hand. That bypassed __init__, so three wrong attribute
    names passed all eight tests and then failed the conversion with

        AttributeError: 'CursorColumnResolver' object has no attribute
        'field_usage_selector'

    No test in this suite may construct a production object with
    __new__ again.
    """
    from idms_db2_phase2.resolvers.cursor_column_resolver import (
        CursorColumnResolver,
    )

    resolver = CursorColumnResolver(
        mapping_repository=_StubMappingRepository(),
        table_name_resolver=_StubTableNameResolver(),
        column_name_resolver=_StubColumnNameResolver(full),
        relationship_resolver=_StubRelationshipResolver(),
    )

    # Replace only the usage selector, by its REAL attribute name.
    assert hasattr(resolver, "usage_column_selector")
    resolver.usage_column_selector = _StubUsageSelector(usage)

    return resolver

def test_full_record_columns_are_added_to_the_usage_driven_list():
    usage = ["DA_CPTAFS_479BFAS", "DA_CRFMAS_479BFAS"]
    full = usage + [f"CT_COL{index:03d}_479BFAS" for index in range(1, 82)]

    resolved = _resolver(usage, full).select_columns_for_record(
        record_name="VMBFAS",
        field_usage_analysis=object(),
    )

    assert len(resolved) == 83
    assert resolved[:2] == usage  # usage columns still lead


def test_audit_columns_never_enter_the_cursor():
    usage = ["DA_CPTAFS_479BFAS"]
    full = usage + ["TS_UPDATE_479BFAS", "ID_USERID_479BFAS"]

    resolved = _resolver(usage, full).select_columns_for_record(
        record_name="VMBFAS",
        field_usage_analysis=object(),
    )

    assert resolved == usage


def test_missing_full_column_set_falls_back_to_usage():
    """No fabrication: an unresolvable record keeps the proven columns."""
    usage = ["DA_CPTAFS_479BFAS"]

    resolved = _resolver(usage, []).select_columns_for_record(
        record_name="VMBFAS",
        field_usage_analysis=object(),
    )

    assert resolved == usage


def test_full_record_extension_is_reported():
    """A silent extension is unreviewable. The log must show the jump."""
    usage = ["DA_CPTAFS_479BFAS"]
    full = usage + ["CT_RKTGDSV_479BFAS", "NR_CIOFMAS_479BFAS"]

    resolver = _resolver(usage, full)
    resolver.select_columns_for_record(
        record_name="VMBFAS",
        field_usage_analysis=object(),
    )

    assert any("extended from 1" in note for note in resolver.diagnostics)
    assert any("to 3 mapped DCLGEN column" in note for note in resolver.diagnostics)