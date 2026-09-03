from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EnhancementResult:
    converted_cobol: str
    diagnostics: list[str] = field(default_factory=list)