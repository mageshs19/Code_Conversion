from __future__ import annotations

from rules.name_derivation_rules import (
    NAME_DERIVATION_TARGET_MARKER,
    VM_BD_NAME_PATTERN,
)


class NameDerivationResolver:
    """Derives DB2-era COBOL names from the VM...BD... source shape.

    Generic and deterministic:
      VM <site>? BD <tail>  ->  VMDZ <site>? <tail>

    Examples:
      VM1BD567 -> VMDZ1567
      VMBD205I -> VMDZ205I

    Does not hardcode any program, record, or copybook name. If a name does
    not match the VM...BD... shape, it is returned unchanged.
    """

    def derive(self, name: str) -> str:
        source = str(name or "").strip()
        if not source:
            return source

        match = VM_BD_NAME_PATTERN.match(source)
        if not match:
            return source

        prefix = match.group("prefix")
        site = match.group("site") or ""
        tail = match.group("tail")

        # Preserve the original case of prefix; DZ marker uppercase.
        return f"{prefix}{NAME_DERIVATION_TARGET_MARKER}{site}{tail}".upper()

    def is_derivable(self, name: str) -> bool:
        return bool(VM_BD_NAME_PATTERN.match(str(name or "").strip()))