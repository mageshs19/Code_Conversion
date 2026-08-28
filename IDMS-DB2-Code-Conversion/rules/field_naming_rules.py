# LOCATION: rules/field_naming_rules.py
# ACTION: REPLACE ENTIRE FILE (add audit prefixes to your existing canonical_field_key)

"""
Deterministic field-naming rules.

Sheet Mapping is the authority: each row pairs a COBOL-side identifier
(`cobol_zone` / `reference_field_name_copybook`) with `new_db2_field_name`
(the DB2 column). Resolution is an exact canonical-key lookup on the SAME
row. No fuzzy / similarity matching is used.
"""

from __future__ import annotations

INSERT_ONLY_AUDIT_PREFIXES = (
    "TS_CREATE",
)

UPDATE_AUDIT_PREFIXES = (
    "TS_UPDATE",
    "ID_USERID",
    "NR_USERID",
    "ID_USER",
    "NR_USER",
)


def canonical_field_key(name: str) -> str:
    """
    Canonical comparison key: uppercase, strip a leading COBOL level number,
    and remove '-' and '_' separators.

    Examples:
        "03 CT-RK-TGDSV"  -> "CTRKTGDSV"
        "DA-INFSD-GDIFAR" -> "DAINFSDGDIFAR"
        "NR_ID"           -> "NRID"
    """
    text = str(name or "").strip().upper()

    parts = text.split()
    if parts and parts[0].isdigit():
        text = " ".join(parts[1:])

    return text.replace("-", "").replace("_", "").replace(" ", "")