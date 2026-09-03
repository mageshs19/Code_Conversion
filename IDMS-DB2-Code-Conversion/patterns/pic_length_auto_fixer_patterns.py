from __future__ import annotations

"""
PIC length auto-fixer regex patterns.

This module contains regex patterns only.
No transformer logic, parser logic, program names, table names, copybook names,
DCLGEN names, or host variables belong here.
"""

import re


PIC_DECLARATION_PATTERN = re.compile(
    r"^(?P<prefix>\s*\d+\s+)"
    r"(?P<name>[A-Z][A-Z0-9-]*)"
    r"(?P<middle>\s+PIC\s+)"
    r"(?P<pic>S?9|X)"
    r"$(?P<length>\d+)$"
    r"(?P<suffix>.*)$",
    flags=re.IGNORECASE,
)


MOVE_PATTERN = re.compile(
    r"\bMOVE\s+"
    r"(?P<source>[A-Z][A-Z0-9-]*)"
    r"\s+TO\s+"
    r"(?P<target>[A-Z][A-Z0-9-]*)"
    r"\b",
    flags=re.IGNORECASE,
)