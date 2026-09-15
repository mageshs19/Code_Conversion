# LOCATION: rules/mapping_scope_rules.py
# ACTION: CREATE NEW FILE

"""Mapping validation scope rules.

Constants only. No regex, no runtime logic, no program / record / table
names.

WHY THIS EXISTS
---------------
MappingValidator walks the ENTIRE Sheet Mapping workbook and reports any
table carrying rows but no usable DB2 columns. That is correct for a
workbook audit and wrong for a per-program conversion report: a retrieval
program is marked with two blocking errors for restart tables it never
touches.

A mapping gap is only an ERROR for a table the program being converted
actually references. For every other table it is an informational note
about the workbook, and it belongs in the conversion log.
"""

from __future__ import annotations

ENFORCE_MAPPING_SCOPE_FILTER = True

# Rewritten message for a gap on a table this program does not use.
# The 'Mapping scope' prefix classifies as Info, so it drops into the
# conversion log instead of the Errors band.
OUT_OF_SCOPE_TEMPLATE = (
    "Mapping scope: {table} carries no usable DB2 column mapping, but "
    "this program does not reference it. Workbook gap, not a conversion "
    "failure."
)

DIAG_SCOPE_APPLIED = (
    "Mapping scope: {out_of_scope} of {total} mapping gap(s) relate to "
    "tables this program does not reference."
)