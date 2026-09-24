from dataclasses import dataclass, field


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


@dataclass
class IdmsOperation:
    operation: str
    record_name: str = ""
    set_name: str = ""
    line_number: int = 0
    raw_line: str = ""


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


# LOCATION: src/idms_db2_phase2/domain/models.py
# ACTION: REPLACE the existing ConversionInput dataclass

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


# LOCATION: src/idms_db2_phase2/domain/models.py
# ACTION: APPEND (place above ConversionInput)

@dataclass
class LrfPathCommand:
    """One command line inside a SELECT FOR KEYWORD block."""
    verb: str = ""              # FIND / OBTAIN / ERASE / IF
    scope: str = ""             # CURRENT / EACH / FIRST
    record_name: str = ""       # VMBSIAS
    within_name: str = ""       # AR-VMBFRM1 or VMBSIAS-VMBFAS
    where_clause: str = ""      # CALCKEY EQ KY-SIFORM OF VMBSIAS OF LR
    status_actions: dict = field(default_factory=dict)   # {"0307": "RETURN VMBFAS-EOA"}
    line_number: int = 0
    raw_line: str = ""


@dataclass
class LrfPath:
    """One SELECT FOR KEYWORD block."""
    keyword: str = ""           # VMBFAS-BY-VMBSIAS
    path_group_verb: str = ""   # OBTAIN / ERASE / MODIFY / STORE
    logical_record: str = ""    # VMBTL03-R01
    commands: list[LrfPathCommand] = field(default_factory=list)


@dataclass
class LogicalRecord:
    """One ADD LOGICAL RECORD block plus every path that serves it."""
    logical_record_name: str = ""          # VMBTL03-R01
    element_records: list[str] = field(default_factory=list)   # VMBSIAS, VMBFAS
    comments: list[str] = field(default_factory=list)
    paths: list[LrfPath] = field(default_factory=list)
    subschema_name: str = ""               # VMBTS03
    schema_name: str = ""                  # VMBTSCH