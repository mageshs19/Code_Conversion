# LOCATION: tests/conftest.py
# ACTION: CREATE NEW FILE

"""Shared pytest configuration and fixtures.

WHY THIS FILE EXISTS
--------------------
1. sys.path bootstrap.
   The converter lives under src/ while rules/, patterns/ and catalogs/
   sit at the project root, so BOTH must be importable. README documents
   $env:PYTHONPATH = "src;." but a forgotten environment variable then
   reports as a mysterious collection error. Setting it here makes
   `python -m pytest tests -q` work from a clean shell.

2. One shared transformer context.
   build_transformer_context() used to live inside a test module, and
   other test modules imported it with

       from tests.test_idms_statement_transformer import build_transformer_context

   Importing one test module from another depends on rootdir, on pytest's
   import mode and on collection order, and it breaks the moment the file
   is renamed. conftest.py is auto-discovered, so nothing imports anything.

Use either form:

    def test_x(transformer_context):            # fixture
        ...

    def test_y():                               # plain call
        context = build_transformer_context()
"""

from __future__ import annotations

import sys
from pathlib import Path

#
# Path bootstrap. MUST run before any idms_db2_phase2 / rules / patterns
# import below.
#
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

for _candidate in (PROJECT_ROOT, SRC_DIR):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

import pytest  # noqa: E402

from idms_db2_phase2.domain.models import (  # noqa: E402
    DclgenColumn,
    SheetMappingRow,
)
from idms_db2_phase2.generators.sql_error_generator import (  # noqa: E402
    SqlErrorGenerator,
)
from idms_db2_phase2.generators.sql_generator import SqlGenerator  # noqa: E402
from idms_db2_phase2.repositories.dclgen_repository import (  # noqa: E402
    DclgenRepository,
)
from idms_db2_phase2.repositories.mapping_repository import (  # noqa: E402
    MappingRepository,
)
from idms_db2_phase2.resolvers.column_name_resolver import (  # noqa: E402
    ColumnNameResolver,
)
from idms_db2_phase2.resolvers.cursor_name_resolver import (  # noqa: E402
    CursorNameResolver,
)
from idms_db2_phase2.resolvers.host_variable_resolver import (  # noqa: E402
    HostVariableResolver,
)
from idms_db2_phase2.resolvers.table_name_resolver import (  # noqa: E402
    TableNameResolver,
)
from idms_db2_phase2.transformers.idms_statement_transformer import (  # noqa: E402
    IdmsStatementTransformer,
)


def build_sheet_mapping_rows() -> list[SheetMappingRow]:
    """One mapped IDMS record, VMB-FAR, with a CALC primary key."""
    return [
        SheetMappingRow(
            cobol_record_idms="VMB-FAR",
            cobol_zone="NR-ID",
            idms_key="CALC",
            db2_key="PRIMARY KEY",
            new_db2_record="DZBFARTB",
            new_db2_field_name="NR_ID",
        ),
        SheetMappingRow(
            cobol_record_idms="VMB-FAR",
            cobol_zone="CD-NAME",
            new_db2_record="DZBFARTB",
            new_db2_field_name="CD_NAME",
        ),
    ]


def build_dclgen_columns() -> list[DclgenColumn]:
    """DCLGEN view DZBFARTV for the mapped record."""
    return [
        DclgenColumn(
            table_name="DZBFARTV",
            column_name="NR_ID",
            cobol_host_name="NR-ID",
        ),
        DclgenColumn(
            table_name="DZBFARTV",
            column_name="CD_NAME",
            cobol_host_name="CD-NAME",
        ),
    ]


def build_transformer_context() -> dict:
    """Fully wired IdmsStatementTransformer plus its collaborators.

    Returned keys:
        mapping_repository
        dclgen_repository
        table_resolver
        host_resolver
        statement_transformer
    """
    mapping_repository = MappingRepository(build_sheet_mapping_rows())
    dclgen_repository = DclgenRepository(build_dclgen_columns())

    table_resolver = TableNameResolver(
        mapping_repository=mapping_repository,
        dclgen_repository=dclgen_repository,
    )

    column_resolver = ColumnNameResolver(
        mapping_repository=mapping_repository,
        dclgen_repository=dclgen_repository,
        table_name_resolver=table_resolver,
    )

    host_resolver = HostVariableResolver(
        dclgen_repository=dclgen_repository,
        table_name_resolver=table_resolver,
    )

    cursor_resolver = CursorNameResolver()

    sql_generator = SqlGenerator(
        mapping_repository=mapping_repository,
        dclgen_repository=dclgen_repository,
        table_name_resolver=table_resolver,
        column_name_resolver=column_resolver,
        host_variable_resolver=host_resolver,
    )

    statement_transformer = IdmsStatementTransformer(
        sql_generator=sql_generator,
        sql_error_generator=SqlErrorGenerator(),
        table_name_resolver=table_resolver,
        cursor_name_resolver=cursor_resolver,
    )

    return {
        "mapping_repository": mapping_repository,
        "dclgen_repository": dclgen_repository,
        "table_resolver": table_resolver,
        "host_resolver": host_resolver,
        "statement_transformer": statement_transformer,
    }


#
# Fixtures
#
@pytest.fixture
def transformer_context() -> dict:
    """Fresh transformer context per test. Never shared between tests."""
    return build_transformer_context()


@pytest.fixture
def statement_transformer(transformer_context) -> IdmsStatementTransformer:
    """The wired IdmsStatementTransformer on its own."""
    return transformer_context["statement_transformer"]


@pytest.fixture
def transform_line(statement_transformer):
    """Convert one IDMS line. Returns (joined_text, opened_set)."""

    def _transform(
        line: str,
        current_division: str = "PROCEDURE",
        sql_error_paragraph: str = "SQL-ERROR",
    ) -> tuple[str, str]:
        lines, opened_set = statement_transformer.transform_line(
            line=line,
            current_division=current_division,
            sql_error_paragraph=sql_error_paragraph,
        )
        return "\n".join(lines), opened_set

    return _transform