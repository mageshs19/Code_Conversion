from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional


def value(
    item: Any,
    *names: str,
    default: Any = None,
) -> Any:
    if item is None:
        return default

    if isinstance(item, dict):
        for name in names:
            item_value = item.get(name)
            if item_value not in (None, ""):
                return item_value

    for name in names:
        if hasattr(item, name):
            item_value = getattr(item, name)
            if item_value not in (None, ""):
                return item_value

    return default


def upper(value: Any) -> str:
    return str(value or "").strip().upper()


def norm_name(value: Any) -> str:
    text = upper(value)
    text = text.replace("_", "-")
    text = re.sub(r"[^A-Z0-9-]", "", text)
    return text


def sql_name(value: Any) -> str:
    text = upper(value)
    text = text.replace("-", "_")
    text = re.sub(r"[^A-Z0-9_]", "", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def compact(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", upper(value))


def include_from_label(source_label: str) -> str:
    if not source_label:
        return ""

    clean = source_label.replace("\\", "/").split("/")[-1]
    clean = clean.split(".")[0]
    return norm_name(clean)


@dataclass
class CobolFileInfo:
    name: str
    assignment: str = ""
    fd_record: str = ""
    record_length: int = 0
    read_target: str = ""


@dataclass
class CopybookRecordInfo:
    include_name: str
    record_name: str
    source_label: str = ""
    fields: set[str] = field(default_factory=set)
    estimated_length: int = 0


@dataclass
class DclgenRoleInfo:
    table_name: str
    include_name: str
    host_record_name: str
    program_column: str
    phase_column: str
    date_column: str
    status_column: str
    retention_column: str
    payload_column: str
    program_field: str
    phase_field: str
    date_field: str
    status_field: str
    retention_field: str
    payload_group: str
    payload_len_field: str
    payload_text_field: str


@dataclass
class UpdateProgramContext:
    input_file: CobolFileInfo
    input_copybook: CopybookRecordInfo
    restart_dclgen: Optional[DclgenRoleInfo]
    program_id: str
    legacy_eof_switch: str = ""
    source_program_text: str = ""
    diagnostics: list[str] = field(default_factory=list)

    @property
    def input_record_name(self) -> str:
        return self.input_copybook.record_name or self.input_copybook.include_name

    @property
    def copybook_include_name(self) -> str:
        return self.input_copybook.include_name or self.input_record_name

    @property
    def record_length(self) -> int:
        if self.input_file.record_length:
            return self.input_file.record_length

        if self.input_copybook.estimated_length:
            return self.input_copybook.estimated_length

        return 1