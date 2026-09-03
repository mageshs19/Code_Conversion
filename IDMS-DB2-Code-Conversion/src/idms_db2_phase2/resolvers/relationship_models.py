from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RelationshipCondition:
    child_record: str
    child_table: str
    child_column: str
    parent_record: str
    parent_table: str
    parent_column: str
    parent_host_reference: str


@dataclass
class RelationshipResolution:
    child_record: str
    parent_record: str = ""
    child_table: str = ""
    parent_table: str = ""
    conditions: list[RelationshipCondition] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)