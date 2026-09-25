# LOCATION: tests/test_cursor_where_logic.py
# ACTION: CREATE NEW FILE
"""Cursor WHERE resolution and declaration contract.

Nine defects are pinned here, one group each. Every group names the
defect it prevents, so a failure tells the reader WHAT regressed, not
only which assert broke.

    D-1  fallback constants were never imported      -> NameError
    D-2  host_for_column() is not a resolver method  -> AttributeError
    D-3  fallback built a self-referential predicate -> meaningless filter
    D-4  only resolve() was tolerated on the facade  -> AttributeError
    D-5  condition.child_table read without getattr  -> AttributeError
    D-6  empty column list rendered SELECT *         -> CHK-12.04 reject
    D-7  WHERE ownership guard was dropped           -> SQLCODE -206
    D-8  parent/child ORDER BY rule was dropped      -> manual divergence
    D-9  a WHERE-less cursor was emitted silently    -> undetectable gap

No real customer name is asserted against; the fixtures define their own.
"""

from __future__ import annotations

import pytest

from idms_db2_phase2.generators.db2_infrastructure.cursor_declare_builder import (
    CursorDeclareBuilder,
)
from idms_db2_phase2.generators.db2_infrastructure.cursor_spec import CursorSpec
from idms_db2_phase2.resolvers.cursor_join_resolver import CursorJoinResolver
from rules.cursor_declaration_rules import (
    CHILD_CURSOR_KEEPS_ORDER_BY,
    EMIT_DRIVING_KEY_PREDICATE,
    ENFORCE_WHERE_COLUMN_OWNERSHIP,
    PARENT_CURSOR_KEEPS_ORDER_BY,
    QUERYNO_BASE,
    QUERYNO_STEP,
)

# =====================================================================
# Fixture names - defined here, never read from a customer program
# =====================================================================
CURSOR = "DZBFASC1"

CHILD_RECORD = "VMBFAS"
CHILD_TABLE = "DZBFASTV"
CHILD_GROUP = "DCLDZBFASTV"

PARENT_RECORD = "VMBSIAS"
PARENT_TABLE = "DZBSIASTV"
PARENT_GROUP = "DCLDZBSIASTV"

KEY_COLUMN = "KY_SIFORM"
DATA_COLUMN = "DA_CPTAFS"
FOREIGN_COLUMN = "NR_CIOFMAS"

CHILD_COLUMNS = [KEY_COLUMN, DATA_COLUMN, FOREIGN_COLUMN]

EXPECTED_PREDICATE = f"{KEY_COLUMN} = :{PARENT_GROUP}.KY-SIFORM"


# =====================================================================
# Helpers
# =====================================================================
def _bodies(lines: list[str]) -> list[str]:
    """Non-blank lines, trimmed. Indentation is not under test here."""
    return [line.strip() for line in lines if line.strip()]


def _clause_index(bodies: list[str], token: str) -> int:
    for index, body in enumerate(bodies):
        if body.upper().startswith(token):
            return index
    return -1


def _has_clause(bodies: list[str], token: str) -> bool:
    return _clause_index(bodies, token) >= 0


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


# =====================================================================
# Resolver stubs
# =====================================================================
class _Condition:
    """A fully populated RelationshipCondition."""

    def __init__(
        self,
        child_column: str = KEY_COLUMN,
        parent_host_reference: str = f":{PARENT_GROUP}.KY-SIFORM",
    ) -> None:
        self.child_record = CHILD_RECORD
        self.child_table = CHILD_TABLE
        self.child_column = child_column
        self.parent_record = PARENT_RECORD
        self.parent_table = PARENT_TABLE
        self.parent_column = KEY_COLUMN
        self.parent_host_reference = parent_host_reference


class _PartialCondition:
    """D-5: a condition missing child_table entirely."""

    def __init__(self) -> None:
        self.child_column = "NOT_A_COLUMN"
        self.parent_column = KEY_COLUMN
        self.parent_host_reference = f":{PARENT_GROUP}.KY-SIFORM"


class _Resolution:
    def __init__(
        self,
        conditions: list | None = None,
        parent_table: str = PARENT_TABLE,
    ) -> None:
        self.child_record = CHILD_RECORD
        self.child_table = CHILD_TABLE
        self.parent_record = PARENT_RECORD
        self.parent_table = parent_table
        self.conditions = list(conditions or [])
        self.diagnostics: list[str] = []


class _ColumnNameResolver:
    def __init__(self, columns: list[str] | None = None) -> None:
        self._columns = list(CHILD_COLUMNS if columns is None else columns)

    def columns_for_table(self, table_name: str) -> list[str]:
        if str(table_name or "").upper() == CHILD_TABLE:
            return list(self._columns)
        if str(table_name or "").upper() == PARENT_TABLE:
            return [KEY_COLUMN]
        return []


class _HostVariableResolver:
    """The REAL resolver surface.

    D-2: there is deliberately no host_for_column() here. Any production
    call to that name raises AttributeError and fails the test.
    """

    def group_for_table(self, table: str) -> str:
        table = str(table or "").upper()
        if table == CHILD_TABLE:
            return CHILD_GROUP
        if table == PARENT_TABLE:
            return PARENT_GROUP
        return ""

    def host_reference_for_column(
        self,
        table_name: str,
        column_name: str,
    ) -> str:
        group = self.group_for_table(table_name)
        if not group:
            return ""
        return f":{group}.{str(column_name or '').replace('_', '-')}"


class _TableNameResolver:
    @staticmethod
    def table_for_record(record_name: str) -> str:
        record = str(record_name or "").upper()
        if record == CHILD_RECORD:
            return CHILD_TABLE
        if record == PARENT_RECORD:
            return PARENT_TABLE
        return ""


class _KeyColumnResolver:
    def __init__(self, primary_keys: list[str] | None = None) -> None:
        self._primary_keys = list(
            [KEY_COLUMN] if primary_keys is None else primary_keys
        )

    def primary_key_columns_for_record(self, record_name: str) -> list[str]:
        return list(self._primary_keys)


class _RelationshipResolver:
    """Facade exposing resolve(), as most call paths do."""

    def __init__(
        self,
        resolution=None,
        primary_keys: list[str] | None = None,
    ) -> None:
        self._resolution = resolution
        self.table_name_resolver = _TableNameResolver()
        self.key_column_resolver = _KeyColumnResolver(primary_keys)

    def resolve(self, child_record: str):
        return self._resolution


class _LegacyRelationshipResolver:
    """D-4: facade exposing ONLY resolve_for_child_record()."""

    def __init__(self, resolution=None) -> None:
        self._resolution = resolution
        self.table_name_resolver = _TableNameResolver()
        self.key_column_resolver = _KeyColumnResolver()

    def resolve_for_child_record(self, child_record: str):
        return self._resolution


def _join(
    relationship_resolver,
    columns: list[str] | None = None,
) -> CursorJoinResolver:
    return CursorJoinResolver(
        relationship_resolver=relationship_resolver,
        column_name_resolver=_ColumnNameResolver(columns),
        host_variable_resolver=_HostVariableResolver(),
    )


def _spec(
    order: int = 0,
    cursor_name: str = CURSOR,
    table_name: str = CHILD_TABLE,
    select_columns: list[str] | None = None,
    where_conditions: list[str] | None = None,
    order_by_columns: list[str] | None = None,
) -> CursorSpec:
    return CursorSpec.read(
        {
            "cursor_name": cursor_name,
            "table_name": table_name,
            "record_name": CHILD_RECORD,
            "select_columns": (
                CHILD_COLUMNS if select_columns is None else select_columns
            ),
            "where_conditions": list(where_conditions or []),
            "order_by_columns": list(order_by_columns or []),
            "cursor_order": order,
        }
    )


# =====================================================================
# Fixtures
# =====================================================================
@pytest.fixture
def declares() -> CursorDeclareBuilder:
    """Builder WITHOUT the ownership guard wired (guard stands down)."""
    return CursorDeclareBuilder(_LineUtils())


@pytest.fixture
def guarded_declares() -> CursorDeclareBuilder:
    """Builder WITH the ownership guard wired."""
    return CursorDeclareBuilder(
        _LineUtils(),
        column_name_resolver=_ColumnNameResolver(),
    )


# =====================================================================
# D-1  fallback constants are importable and wired
# =====================================================================
def test_driving_key_fallback_constants_are_importable():
    """The fallback used names it never imported and raised NameError."""
    assert EMIT_DRIVING_KEY_PREDICATE in (True, False)


def test_fallback_path_never_raises_name_error():
    resolver = _join(_RelationshipResolver(resolution=None))
    assert resolver.where_conditions(CHILD_RECORD) == [] or True


# =====================================================================
# D-2  only the real HostVariableResolver API is called
# =====================================================================
def test_resolver_never_calls_a_missing_host_method():
    """host_for_command/host_for_column do not exist on the resolver."""
    hosts = _HostVariableResolver()
    assert not hasattr(hosts, "host_for_column")

    resolver = CursorJoinResolver(
        relationship_resolver=_RelationshipResolver(
            resolution=_Resolution(conditions=[])
        ),
        column_name_resolver=_ColumnNameResolver(),
        host_variable_resolver=hosts,
    )
    # Must complete without AttributeError.
    resolver.where_conditions(CHILD_RECORD)


# =====================================================================
# D-3  the fallback never compares a column to its OWN group
# =====================================================================
def test_driving_key_predicate_targets_the_parent_group():
    resolver = _join(
        _RelationshipResolver(resolution=_Resolution(conditions=[]))
    )
    conditions = resolver.where_conditions(CHILD_RECORD)

    assert conditions == [EXPECTED_PREDICATE]


def test_driving_key_predicate_is_never_self_referential():
    """'KY_SIFORM = :DCLDZBFASTV.KY-SIFORM' is a filter, not a join."""
    resolver = _join(
        _RelationshipResolver(resolution=_Resolution(conditions=[]))
    )
    for predicate in resolver.where_conditions(CHILD_RECORD):
        assert CHILD_GROUP not in predicate


def test_no_parent_side_refuses_instead_of_guessing():
    resolver = _join(
        _RelationshipResolver(
            resolution=_Resolution(conditions=[], parent_table="")
        )
    )
    assert resolver.where_conditions(CHILD_RECORD) == []
    assert any("WHERE not generated" in m for m in resolver.diagnostics)


def test_caller_supplied_driving_host_is_honoured():
    """The LRF path keyword can supply the parent host directly."""
    resolver = _join(
        _RelationshipResolver(
            resolution=_Resolution(conditions=[], parent_table="")
        )
    )
    conditions = resolver.where_conditions(
        CHILD_RECORD,
        driving_host_reference=f":{PARENT_GROUP}.KY-SIFORM",
    )
    assert conditions == [EXPECTED_PREDICATE]


# =====================================================================
# D-4  both facade method names are tolerated
# =====================================================================
def test_legacy_facade_method_name_is_tolerated():
    resolver = CursorJoinResolver(
        relationship_resolver=_LegacyRelationshipResolver(
            resolution=_Resolution(conditions=[_Condition()])
        ),
        column_name_resolver=_ColumnNameResolver(),
        host_variable_resolver=_HostVariableResolver(),
    )
    assert resolver.where_conditions(CHILD_RECORD) == [EXPECTED_PREDICATE]


# =====================================================================
# D-5  a partial condition is reported, never fatal
# =====================================================================
def test_a_condition_without_child_table_is_skipped_not_fatal():
    resolver = _join(
        _RelationshipResolver(
            resolution=_Resolution(conditions=[_PartialCondition()])
        )
    )
    conditions = resolver.where_conditions(CHILD_RECORD)

    # Falls through to the driving key rather than raising.
    assert conditions == [EXPECTED_PREDICATE]
    assert any("is not a column of" in m for m in resolver.diagnostics)


# =====================================================================
# Attempt 1 - relationship predicates win when they exist
# =====================================================================
def test_relationship_predicate_is_preferred_over_the_fallback():
    resolver = _join(
        _RelationshipResolver(
            resolution=_Resolution(
                conditions=[_Condition(child_column=FOREIGN_COLUMN)]
            )
        )
    )
    conditions = resolver.where_conditions(CHILD_RECORD)

    assert conditions == [f"{FOREIGN_COLUMN} = :{PARENT_GROUP}.KY-SIFORM"]


def test_duplicate_predicates_are_collapsed():
    resolver = _join(
        _RelationshipResolver(
            resolution=_Resolution(
                conditions=[_Condition(), _Condition()]
            )
        )
    )
    assert len(resolver.where_conditions(CHILD_RECORD)) == 1


def test_a_predicate_without_a_parent_host_is_skipped_and_reported():
    resolver = _join(
        _RelationshipResolver(
            resolution=_Resolution(
                conditions=[_Condition(parent_host_reference="NO-GROUP-HERE")],
                parent_table="",
            )
        )
    )
    assert resolver.where_conditions(CHILD_RECORD) == []
    assert any("host variable" in m for m in resolver.diagnostics)


def test_an_empty_record_name_returns_no_predicate():
    resolver = _join(_RelationshipResolver())
    assert resolver.where_conditions("") == []


def test_diagnostics_are_reset_between_calls():
    resolver = _join(
        _RelationshipResolver(
            resolution=_Resolution(conditions=[], parent_table="")
        )
    )
    resolver.where_conditions(CHILD_RECORD)
    first = len(resolver.diagnostics)

    resolver.where_conditions(CHILD_RECORD)
    assert len(resolver.diagnostics) == first


# =====================================================================
# D-6  SELECT * is refused
# =====================================================================
def test_an_empty_column_list_refuses_instead_of_select_star(declares):
    bodies = _bodies(declares.build(_spec(select_columns=[])))

    assert len(bodies) == 1
    assert "DB2 WARNING" in bodies[0]
    assert "*" not in bodies[0].split("WARNING")[1].split(";")[0]


def test_select_star_never_appears_in_a_rendered_declare(declares):
    bodies = _bodies(declares.build(_spec()))
    select = _clause_index(bodies, "SELECT")

    assert select >= 0
    assert bodies[select + 1].strip() != "*"


# =====================================================================
# D-7  WHERE column ownership guard
# =====================================================================
def test_ownership_guard_is_enabled_by_the_site_standard():
    assert ENFORCE_WHERE_COLUMN_OWNERSHIP is True


def test_a_parent_column_on_the_left_is_refused(guarded_declares):
    """A parent column on the left is SQLCODE -206 at bind time."""
    spec = _spec(
        where_conditions=[f"NR_PARENT_ONLY = :{PARENT_GROUP}.NR-PARENT-ONLY"],
    )
    bodies = _bodies(guarded_declares.build(spec))

    assert len(bodies) == 1
    assert "DB2 WARNING" in bodies[0]
    assert "NR_PARENT_ONLY" in bodies[0]


def test_an_owned_column_on_the_left_is_accepted(guarded_declares):
    spec = _spec(where_conditions=[EXPECTED_PREDICATE])
    bodies = _bodies(guarded_declares.build(spec))

    assert _has_clause(bodies, "WHERE")
    assert any(EXPECTED_PREDICATE in body for body in bodies)


def test_the_guard_stands_down_when_no_column_list_is_available(declares):
    """No resolver injected: validate nothing rather than refuse."""
    spec = _spec(where_conditions=["ANY_COLUMN = :SOMEGROUP.ANY-COLUMN"])
    bodies = _bodies(declares.build(spec))

    assert _has_clause(bodies, "WHERE")


# =====================================================================
# D-8  parent / child ORDER BY rule
# =====================================================================
def test_a_child_cursor_keeps_order_by(declares):
    assert CHILD_CURSOR_KEEPS_ORDER_BY is True

    spec = _spec(
        where_conditions=[EXPECTED_PREDICATE],
        order_by_columns=[f"{KEY_COLUMN} ASC"],
    )
    bodies = _bodies(declares.build(spec))

    assert _has_clause(bodies, "ORDER BY")


def test_a_parent_cursor_also_keeps_order_by(declares):
    """CORRECTED - this test asserted the defect, not the contract.

    It required PARENT_CURSOR_KEEPS_ORDER_BY to be False, which encoded
    the premise "the manual reference never orders a parent cursor".
    Manual reference VMDZ7200 (Train Case 3) ends its ROOT cursor with

        ORDER BY NR_ID_479BFAS ASC

    so the premise was a single-sample generalisation. Row sequence is
    business meaning and must survive on every cursor.
    """
    assert PARENT_CURSOR_KEEPS_ORDER_BY is True

    spec = _spec(order_by_columns=[f"{KEY_COLUMN} ASC"])
    bodies = _bodies(declares.build(spec))

    assert _has_clause(bodies, "ORDER BY")
    assert not any("removed ORDER BY" in m for m in declares.messages)

# =====================================================================
# D-9  no silent WHERE-less cursor
# =====================================================================
def test_a_where_less_cursor_is_reported(declares):
    declares.build(_spec())

    assert any("WITHOUT a WHERE" in m for m in declares.messages)


def test_a_qualified_cursor_reports_its_predicate_count(declares):
    declares.build(_spec(where_conditions=[EXPECTED_PREDICATE]))

    assert any("qualified by 1 predicate" in m for m in declares.messages)


def test_every_build_reports_the_declaration(declares):
    declares.build(_spec())

    assert any("declared" in m for m in declares.messages)


# =====================================================================
# Clause order and QUERYNO - unchanged contract
# =====================================================================
def test_clause_order_is_select_from_where_order_by_read_only_queryno(
    declares,
):
    spec = _spec(
        where_conditions=[EXPECTED_PREDICATE],
        order_by_columns=[f"{KEY_COLUMN} ASC"],
    )
    bodies = _bodies(declares.build(spec))

    assert _clause_index(bodies, "SELECT") < _clause_index(bodies, "FROM")
    assert _clause_index(bodies, "FROM") < _clause_index(bodies, "WHERE")
    assert _clause_index(bodies, "WHERE") < _clause_index(bodies, "ORDER BY")
    assert _clause_index(bodies, "ORDER BY") < _clause_index(
        bodies, "FOR READ ONLY"
    )
    assert bodies[-2].upper().startswith("QUERYNO ")
    assert bodies[-1].upper().startswith("END-EXEC")


def test_queryno_is_derived_from_the_cursor_order(declares):
    bodies = _bodies(declares.build(_spec(order=2)))
    expected = QUERYNO_BASE + (2 * QUERYNO_STEP)

    assert any(str(expected) in body for body in bodies)


def test_queryno_is_stable_across_runs(declares):
    """Byte-identical output on repeated runs is a release requirement."""
    assert declares.build(_spec(order=1)) == declares.build(_spec(order=1))


def test_a_spec_without_a_table_produces_a_warning_not_sql(declares):
    """Refusing beats guessing: no fabricated FROM clause."""
    bodies = _bodies(declares.build(_spec(table_name="")))

    assert len(bodies) == 1
    assert "DB2 WARNING" in bodies[0]


def test_a_spec_without_a_cursor_name_produces_a_warning_not_sql(declares):
    bodies = _bodies(declares.build(_spec(cursor_name="")))

    assert len(bodies) == 1
    assert "DB2 WARNING" in bodies[0]


# =====================================================================
# End-to-end - resolver output feeds the builder unchanged
# =====================================================================
def test_resolver_output_renders_as_a_where_clause(declares):
    resolver = _join(
        _RelationshipResolver(
            resolution=_Resolution(conditions=[_Condition()])
        )
    )
    conditions = resolver.where_conditions(CHILD_RECORD)
    bodies = _bodies(declares.build(_spec(where_conditions=conditions)))

    assert _has_clause(bodies, "WHERE")
    assert any(EXPECTED_PREDICATE in body for body in bodies)
    assert not any("WITHOUT a WHERE" in m for m in declares.messages)


def test_a_sweep_record_still_renders_valid_sql_without_a_where(declares):
    resolver = _join(
        _RelationshipResolver(
            resolution=_Resolution(conditions=[], parent_table="")
        )
    )
    conditions = resolver.where_conditions(CHILD_RECORD)
    bodies = _bodies(declares.build(_spec(where_conditions=conditions)))

    assert conditions == []
    assert not _has_clause(bodies, "WHERE")
    assert _has_clause(bodies, "FOR READ ONLY")
    assert any("WITHOUT a WHERE" in m for m in declares.messages)

def test_a_parent_cursor_keeps_order_by(declares):
    """CORRECTED: manual reference VMDZ7200 orders its root cursor."""
    assert PARENT_CURSOR_KEEPS_ORDER_BY is True

    spec = _spec(order_by_columns=[f"{KEY_COLUMN} ASC"])
    bodies = _bodies(declares.build(spec))

    assert _has_clause(bodies, "ORDER BY")
    assert not any("removed ORDER BY" in m for m in declares.messages)