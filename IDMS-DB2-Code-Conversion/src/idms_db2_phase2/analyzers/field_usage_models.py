from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FieldUsage:
    record_name: str
    condition_fields: set[str] = field(default_factory=set)
    output_fields: set[str] = field(default_factory=set)
    move_source_fields: set[str] = field(default_factory=set)
    move_target_fields: set[str] = field(default_factory=set)
    dclgen_host_fields: set[str] = field(default_factory=set)
    all_fields: set[str] = field(default_factory=set)


@dataclass
class FieldUsageAnalysis:
    usage_by_record: dict[str, FieldUsage] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)