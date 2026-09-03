from __future__ import annotations

import re

# Deterministic COBOL name-derivation rules.
#
# Constants + a single pure regex here (this file is the authority for the
# VM...BD... -> VMDZ... site transform). No program names, record names,
# copybook names, DB2 tables, DCLGEN names, or host variables are hardcoded.
#
# Rule (applies to PROGRAM-ID and to input record / copybook names):
#   VM <site>? BD <tail>  ->  VMDZ <site>? <tail>
#
# Examples:
#   VM1BD567 -> VMDZ1567     (site '1' preserved after DZ)
#   VMBD205I -> VMDZ205I     (no site char; BD simply becomes DZ)
#
# Structure captured:
#   prefix  = "VM"           (fixed)
#   site    = optional single character between VM and BD (e.g. "1")
#   marker  = "BD"           -> replaced by "DZ"
#   tail    = everything after BD (e.g. "567", "205I")

NAME_DERIVATION_RULES = [
    "Derive DB2-era names from the VM...BD... source shape.",
    "Replace the BD marker with DZ.",
    "Preserve an optional single site character (VM<site>BD -> VMDZ<site>).",
    "Preserve the trailing characters unchanged.",
    "Do not hardcode any program, record, or copybook name.",
]

NAME_DERIVATION_PREFIX = "VM"
NAME_DERIVATION_SOURCE_MARKER = "BD"
NAME_DERIVATION_TARGET_MARKER = "DZ"

# VM  (site?)  BD  (tail)
# site is at most one character; tail is the remainder.
VM_BD_NAME_PATTERN = re.compile(
    r"^(?P<prefix>VM)(?P<site>[A-Z0-9]?)"
    r"(?P<marker>BD)"
    r"(?P<tail>[A-Z0-9]+)$",
    flags=re.IGNORECASE,
)