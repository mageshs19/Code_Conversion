"""The single input object for a code review run. Data only.

Everything a check is allowed to see arrives here. Checks never read files,
never call the converter and never reach into session state.

Dependency direction is one-way: this module imports nothing from the
converter, and the converter never imports from code_review.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# --------------------------------------------------------------------------
# Program kinds
#
# Values are UPPERCASE because Check.applies() compares them against
# check_base.RETRIEVAL / UPDATE / BOTH using str(...).upper().
# --------------------------------------------------------------------------
KIND_RETRIEVAL = "RETRIEVAL"
KIND_UPDATE = "UPDATE"
KIND_UNKNOWN = "UNKNOWN"

VALID_KINDS: tuple[str, ...] = (KIND_RETRIEVAL, KIND_UPDATE, KIND_UNKNOWN)


def normalise_kind(value: str) -> str:
    """Returns a known kind, or KIND_UNKNOWN when the value is not recognised."""
    kind = str(value or "").strip().upper()
    return kind if kind in VALID_KINDS else KIND_UNKNOWN


@dataclass
class ReviewContext:
    """Immutable-by-convention input for one program review."""

    program_name: str = ""
    program_kind: str = KIND_UNKNOWN
    target_program_id: str = ""
    source_file: str = ""
    converted_cobol: str = ""
    source_cobol: str = ""
    sheet_mapping_rows: list = field(default_factory=list)
    dclgen_columns: list = field(default_factory=list)
    copybook_fields: list = field(default_factory=list)

    def __post_init__(self) -> None:
        self.program_name = str(self.program_name or "")
        self.program_kind = normalise_kind(self.program_kind)
        self.target_program_id = str(self.target_program_id or "")
        self.source_file = str(self.source_file or "")
        self.converted_cobol = str(self.converted_cobol or "")
        self.source_cobol = str(self.source_cobol or "")
        self.sheet_mapping_rows = list(self.sheet_mapping_rows or [])
        self.dclgen_columns = list(self.dclgen_columns or [])
        self.copybook_fields = list(self.copybook_fields or [])

    # ---- availability -----------------------------------------------------
    def has(self, name: str) -> bool:
        """True when the named input was supplied and is non-empty."""
        if not hasattr(self, str(name)):
            return False
        value = getattr(self, str(name))
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, dict, set)):
            return bool(value)
        return value is not None

    def missing(self, names) -> list[str]:
        """Inputs a check declared in NEEDS that were not supplied.

        Reviewer._one() calls this and reports BLOCKED instead of FAIL.
        """
        return [str(n) for n in (names or ()) if not self.has(str(n))]

    # ---- convenience ------------------------------------------------------
    @property
    def is_retrieval(self) -> bool:
        return self.program_kind == KIND_RETRIEVAL

    @property
    def is_update(self) -> bool:
        return self.program_kind == KIND_UPDATE

    @property
    def has_source(self) -> bool:
        return bool(self.source_cobol.strip())

    @property
    def has_metadata(self) -> bool:
        return bool(
            self.sheet_mapping_rows or self.dclgen_columns or self.copybook_fields
        )

    def describe(self) -> str:
        return (
            f"{self.program_name or '(unnamed)'} "
            f"[{self.program_kind}] -> {self.source_file or '(in memory)'}"
        )


__all__ = [
    "ReviewContext",
    "KIND_RETRIEVAL",
    "KIND_UPDATE",
    "KIND_UNKNOWN",
    "VALID_KINDS",
    "normalise_kind",
]