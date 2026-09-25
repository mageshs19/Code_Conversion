# LOCATION: src/idms_db2_phase2/domain/models.py
# ACTION: REPLACE ENTIRE FILE
"""Domain models shared by parsers, repositories, resolvers and the UI.

Dataclasses only. No parsing, no logic, no I/O, no program / record /
table / column names.

CORRECTION - a dataclass referenced a class defined below it
--------------------------------------------------------------
The LRF models were appended to the END of this module while
ConversionInput, declared earlier, already carried

    logical_records: list[LogicalRecord] = field(default_factory=list)

Without lazy annotations that type is evaluated while the class body
executes, so the name did not exist yet and every import of this module
died with

    NameError: name 'LogicalRecord' is not defined

The failure surfaced through the Streamlit entry point
(app -> main_page -> main_tab -> conversion_actions -> domain.models)
but it is not a Streamlit, Python-version or environment problem: the
module cannot be imported by anything.

TWO GUARDS, deliberately both:

  1. DEFINITION ORDER - every model is declared before the model that
     references it. LRF models therefore sit ABOVE ConversionInput.

  2. LAZY ANNOTATIONS - `from __future__ import annotations` makes the
     order irrelevant to the interpreter, so a future edit that moves a
     class cannot reintroduce the same crash.

Guard 2 does NOT replace guard 1: repositories/lrf_repository.py does a
real runtime import,

    from idms_db2_phase2.domain.models import LogicalRecord, LrfPath

so the names must exist in the module regardless of how annotations are
evaluated.

FIELD NAMES ARE A CONTRACT
--------------------------
lrf_parser.py constructs these objects and lrf_repository.py /
lrf_path_resolver.py read them by attribute. Renaming a field here
breaks those modules silently at runtime, not at import.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# =====================================================================
# Sheet Mapping / DCLGEN / Copybook input models
# =====================================================================


@dataclass
class SheetMappingRow:
    cobol_record_idms: str = ""
    cobol_zone: str = ""
    idms_key: str = ""
    idms_pic_clause: str = ""
    length_of_field_bytes: str = ""
    field_end_position: str = ""
    db2_key: str = ""
    new_db2_record: str = ""
    new_db2_field_name: str = ""
    new_db2_data_type: str = ""
    hopex_expression_type_remark: str = ""
    remarks: str = ""
    relation: str = ""
    reference_field_name_copybook: str = ""
    reference_field_pic_clause: str = ""
    cross_application_db2_table: str = ""
    cross_application_db2_field_name: str = ""
    cross_application_db2_data_type: str = ""
    basetype: str = ""


@dataclass
class DclgenColumn:
    table_name: str = ""
    column_name: str = ""
    db2_type: str = ""
    cobol_host_name: str = ""
    cobol_picture: str = ""
    cobol_usage: str = ""
    nullable: bool = True


@dataclass
class CopybookField:
    level: str = ""
    name: str = ""
    picture: str = ""
    usage: str = ""
    occurs: str = ""


# =====================================================================
# Parsed IDMS source models
# =====================================================================


@dataclass
class IdmsOperation:
    operation: str
    record_name: str = ""
    set_name: str = ""
    line_number: int = 0
    raw_line: str = ""


# =====================================================================
# Metadata summary models (UI and diagnostics)
# =====================================================================


@dataclass
class RelationshipSummary:
    relation: str = ""
    parent_record: str = ""
    child_record: str = ""
    parent_key: str = ""
    child_key: str = ""


@dataclass
class RecordSummary:
    record_name: str
    db2_table: str
    column_count: int
    key_columns: list[str] = field(default_factory=list)


# =====================================================================
# LRF (Logical Record Facility) models
# ---------------------------------------------------------------------
# DECLARED BEFORE ConversionInput - it references LogicalRecord.
# Innermost first: LrfPathCommand -> LrfPath -> LogicalRecord.
# =====================================================================


@dataclass
class LrfPathCommand:
    """One command line inside a SELECT FOR KEYWORD block."""

    verb: str = ""              # FIND / OBTAIN / ERASE / IF
    scope: str = ""             # CURRENT / EACH / FIRST / EMPTY / NOT EMPTY
    record_name: str = ""       # element record the command drives
    within_name: str = ""       # owning area or set
    where_clause: str = ""      # qualification text, upper-cased
    status_actions: dict[str, str] = field(default_factory=dict)
    line_number: int = 0
    raw_line: str = ""


@dataclass
class LrfPath:
    """One SELECT FOR KEYWORD block."""

    keyword: str = ""           # path keyword named by the program
    path_group_verb: str = ""   # OBTAIN / ERASE / MODIFY / STORE
    logical_record: str = ""    # logical record the path serves
    commands: list[LrfPathCommand] = field(default_factory=list)


@dataclass
class LogicalRecord:
    """One ADD LOGICAL RECORD block plus every path that serves it."""

    logical_record_name: str = ""
    element_records: list[str] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    paths: list[LrfPath] = field(default_factory=list)
    subschema_name: str = ""
    schema_name: str = ""


# =====================================================================
# Conversion input / output
# ---------------------------------------------------------------------
# LAST. Every model it references is already defined above.
# =====================================================================


@dataclass
class ConversionInput:
    sheet_mapping_rows: list[SheetMappingRow] = field(default_factory=list)
    dclgen_columns: list[DclgenColumn] = field(default_factory=list)
    copybook_fields: list[CopybookField] = field(default_factory=list)
    logical_records: list[LogicalRecord] = field(default_factory=list)
    idms_cobol_text: str = ""
    target_program_id: str = ""
    auto_fix_pic_length_mismatches: bool = False


@dataclass
class ConversionResult:
    converted_cobol: str = ""
    validation_messages: list[str] = field(default_factory=list)
    operations: list[IdmsOperation] = field(default_factory=list)


__all__ = [
    # inputs
    "SheetMappingRow",
    "DclgenColumn",
    "CopybookField",
    # parsed source
    "IdmsOperation",
    # summaries
    "RelationshipSummary",
    "RecordSummary",
    # LRF
    "LrfPathCommand",
    "LrfPath",
    "LogicalRecord",
    # conversion
    "ConversionInput",
    "ConversionResult",
]