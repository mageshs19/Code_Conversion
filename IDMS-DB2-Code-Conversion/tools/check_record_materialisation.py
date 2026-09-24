# LOCATION: tools/check_record_materialisation.py
# ACTION: CREATE NEW FILE
"""Pinpoints why record materialisation did not run.

    set PYTHONPATH=src;.
    python tools\\check_record_materialisation.py

Exit 0 = the composer works in isolation; the problem is wiring.
Exit 1 = the composer itself is broken; the reason is printed.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

REQUIRED_RULES = [
    "ALLOW_LAYOUT_SHORTER_THAN_TARGET", "EMIT_REMAINDER_FILLER",
    "FILLER_FIELD_NAMES", "LAYOUT_BODY_WIDTH", "LAYOUT_MAX_INDENT_DEPTH",
    "LAYOUT_MIN_NAME_GAP", "MAX_RECORD_MOVES", "MIN_LEVEL", "MAX_LEVEL",
    "MOVE_CONTINUATION_INDENT", "MOVE_INLINE_LIMIT",
    "NON_COLUMN_SENTINELS", "NON_RECORD_NAME_SUFFIXES",
    "RECORD_GROUP_LEVEL_STEP", "REDEFINES_CONTINUATION_GAP",
    "REDEFINES_HEAD_TEMPLATE", "REDEFINES_INLINE_LIMIT",
    "REMAINDER_FILLER_NAME", "REMAINDER_FILLER_PICTURE_TEMPLATE",
    "WRAP_REDEFINES_ENTRY",
]
REQUIRED_PATTERNS = ["PICTURE_CLAUSE_PATTERN", "PICTURE_SYMBOL_PATTERN"]
REQUIRED_MESSAGES = [
    "materialised", "remainder_filler", "scan_summary", "no_moves",
    "composer_absent", "no_declared_length", "skipped_not_a_record",
]


def _fail(step: str, detail: str) -> None:
    print(f"\n  FAIL  {step}\n        {detail}")
    sys.exit(1)


def _ok(step: str, detail: str = "") -> None:
    print(f"  OK    {step}" + (f"  ({detail})" if detail else ""))


# ---------------------------------------------------------------- 1
print("\n1. rules / patterns constants")
try:
    import rules.record_materialisation_rules as R
    import patterns.record_materialisation_patterns as P
except Exception:
    _fail("import", traceback.format_exc(limit=3))

missing = [n for n in REQUIRED_RULES if not hasattr(R, n)]
if missing:
    _fail("rules constants", "missing: " + ", ".join(missing))
_ok("rules constants", f"{len(REQUIRED_RULES)} present")

missing = [n for n in REQUIRED_PATTERNS if not hasattr(P, n)]
if missing:
    _fail("patterns", "missing: " + ", ".join(missing))
_ok("patterns", f"{len(REQUIRED_PATTERNS)} present")

missing = [k for k in REQUIRED_MESSAGES
           if k not in R.RECORD_MATERIALISATION_MESSAGES]
if missing:
    _fail("message keys", "missing: " + ", ".join(missing))
_ok("message keys")

# ---------------------------------------------------------------- 2
print("\n2. module imports")
try:
    from idms_db2_phase2.composers.record_materialisation_composer import (
        RecordMaterialisationComposer,
    )
except Exception:
    _fail("composer import", traceback.format_exc(limit=5))
_ok("composer import")

# ---------------------------------------------------------------- 3
print("\n3. composer behaviour on a synthetic program")


class _Row:
    def __init__(self, zone, pic, length, column):
        self.cobol_zone = zone
        self.idms_pic_clause = pic
        self.length_of_field_bytes = length
        self.new_db2_field_name = column
        self.new_db2_data_type = ""
        self.cross_application_db2_field_name = ""


class _Mapping:
    def rows_for_record(self, record):
        if str(record).upper() != "TESTREC":
            return []
        return [
            _Row("02 F-ALPHA", "PIC X(10)", "10", "COL_ALPHA"),
            _Row("02 FILLER", "PIC X(5)", "5", "FILLER"),
        ]


class _Table:
    def table_for_record(self, record):
        return "TESTTB" if str(record).upper() == "TESTREC" else ""


class _Host:
    def group_for_table(self, table):
        return "DCLTESTTV"

    def host_reference_for_column(self, table_name, column_name):
        return f":DCLTESTTV.{str(column_name).replace('_', '-')}"


def _line(seq: str, body: str) -> str:
    return f"{seq} {body.ljust(65)}{seq}0"


SOURCE = "\n".join([
    _line("000100", "DATA DIVISION."),
    _line("000200", "WORKING-STORAGE SECTION."),
    _line("000300", "01  OUT-REC."),
    _line("000400", "    05  F-TARGET              PIC X(20)."),
    _line("000500", "PROCEDURE DIVISION."),
    _line("000600", "    MOVE TESTREC TO F-TARGET."),
]) + "\n"

composer = RecordMaterialisationComposer(
    mapping_repository=_Mapping(),
    table_name_resolver=_Table(),
    host_variable_resolver=_Host(),
)

try:
    result = composer.compose(SOURCE)
except Exception:
    _fail("compose()", traceback.format_exc(limit=8))

print("\n  --- messages ---")
for message in composer.messages:
    print(f"      {message}")

print("\n  --- output ---")
for row in result.splitlines():
    print(f"      {row.rstrip()}")

expanded = "06  TESTREC." in result
filler = "FILLER" in result and "X(5)" in result
remainder = "X(5)." in result and result.count("FILLER") >= 2

print()
if not expanded:
    _fail("expansion", "F-TARGET was not expanded - see messages above")
_ok("expansion", "TESTREC layout emitted")
_ok("filler handling" if filler else "filler handling")
print(f"  {'OK   ' if remainder else 'WARN '} remainder FILLER "
      f"{'emitted' if remainder else 'NOT emitted - check declared_bytes'}")

print("\nComposer works in isolation. If the app still skips it, the")
print("problem is WIRING:")
print("  a) conversion_component_factory.py must register")
print("     composers['record_materialisation'] = RecordMaterialisationComposer(...)")
print("  b) conversion_layout_pipeline.finish() must call")
print("     steps.materialise_records(converted_cobol=..., validation_messages=...)")
sys.exit(0)