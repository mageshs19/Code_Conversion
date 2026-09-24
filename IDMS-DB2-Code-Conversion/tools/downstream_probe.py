# LOCATION: tools/downstream_probe.py
# ACTION: CREATE NEW FILE

"""Finds which post-conversion pass corrupts a rewritten IF condition.

BACKGROUND
----------
tools/date_rewrite_probe.py proved Db2DateComparisonRewriter emits four
clean 80-column records:

        IF (HELP-DA-CPTAFS-479BFAS < DA-ARCH-YMD
           AND HELP-DA-CPTAFS-479BFAS NOT = '00000000') OR
           (HELP-DA-CRFMAS-479BFAS < DA-ARCH-YMD AND
           HELP-DA-CPTAFS-479BFAS = '00000000')

The generated file contains six records with a stray '0' on three of
them:

        AND 0
        HELP-DA-CPTAFS-479BFAS NOT = '00000000') OR 0
        = '00000000') 0

A bare '0' is the first character of the right sequence area 02610000,
so some pass is reading the body as columns 8-73 instead of 8-72, or is
re-wrapping a body that already carries sequence digits.

This probe feeds the KNOWN-GOOD records to each candidate pass in turn
and reports the first one that changes the line count or introduces a
stray token.

    $env:PYTHONPATH = "src;."
    python tools\downstream_probe.py
"""

from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

for _candidate in (PROJECT_ROOT, SRC_DIR):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

BODY_START = 7
BODY_END = 72
LINE_WIDTH = 80


def fixed(seq: str, body: str, right: str) -> str:
    return f"{seq} {body.ljust(65)}{right}"


# Exactly what the rewriter emits, verified by date_rewrite_probe.
CLEAN = [
    fixed("001750", " PROCEDURE DIVISION.", "01750000"),
    fixed("002290", " BEHANDELING.", "02290000"),
    fixed("002600", "     IF (HELP-DA-CPTAFS-479BFAS < DA-ARCH-YMD", "02600000"),
    fixed("002610", "        AND HELP-DA-CPTAFS-479BFAS NOT = '00000000') OR", "02610000"),
    fixed("002620", "        (HELP-DA-CRFMAS-479BFAS < DA-ARCH-YMD AND", "02620000"),
    fixed("002630", "        HELP-DA-CPTAFS-479BFAS = '00000000')", "02630000"),
    fixed("002660", "        ADD 1              TO WS-TELLER", "02660000"),
    fixed("002770", "     END-IF.", "02770000"),
]

CLEAN_TEXT = "\n".join(CLEAN) + "\n"

# (label, [candidate module paths], class name, method name)
CANDIDATES = [
    (
        "FixedFormatComposer",
        [
            "idms_db2_phase2.composers.fixed_format_composer",
            "idms_db2_phase2.composers.fixed_format",
        ],
        "FixedFormatComposer",
        ("format", "compose"),
    ),
    (
        "ProcedureIndentNormalizer",
        [
            "idms_db2_phase2.services.procedure_indent_normalizer",
            "idms_db2_phase2.composers.procedure_indent_normalizer",
        ],
        "ProcedureIndentNormalizer",
        ("compose", "format"),
    ),
    (
        "CobolAreaAlignmentReflow",
        [
            "idms_db2_phase2.services.cobol_area_alignment_reflow",
        ],
        "CobolAreaAlignmentReflow",
        ("compose", "reflow"),
    ),
    (
        "SequenceArtifactCleanupComposer",
        [
            "idms_db2_phase2.composers.sequence_artifact_cleanup_composer",
        ],
        "SequenceArtifactCleanupComposer",
        ("compose",),
    ),
    (
        "FinalSequenceResequencerService",
        [
            "idms_db2_phase2.services.final_sequence_resequencer_service",
        ],
        "FinalSequenceResequencerService",
        ("resequence", "compose"),
    ),
    (
        "FinalCobolFixComposer",
        [
            "idms_db2_phase2.composers.final_cobol_fix_composer",
        ],
        "FinalCobolFixComposer",
        ("compose", "format"),
    ),
    (
        "StructuralSafetyComposer",
        [
            "idms_db2_phase2.composers.structural_safety_composer",
        ],
        "StructuralSafetyComposer",
        ("compose",),
    ),
]

STRAY_MARKERS = (" 0", "AND 0", "OR 0", "') 0")


def load(paths: list[str], class_name: str):
    for path in paths:
        try:
            module = importlib.import_module(path)
        except Exception:  # noqa: BLE001
            continue

        target = getattr(module, class_name, None)

        if target is not None:
            return target, path

    return None, ""


def condition_bodies(text: str) -> list[str]:
    output = []

    for line in str(text or "").splitlines():
        body = line[BODY_START:BODY_END] if len(line) >= BODY_END else line[BODY_START:]
        body = body.rstrip()

        if "HELP-DA-" in body and "MOVE" not in body:
            output.append(body)

    return output


BASELINE = condition_bodies(CLEAN_TEXT)


def report(label: str, module_path: str, text: str) -> bool:
    bodies = condition_bodies(text)
    broken = False

    print(f"\n{label}")
    print(f"  module: {module_path}")
    print(f"  condition records: {len(BASELINE)} -> {len(bodies)}")

    if len(bodies) != len(BASELINE):
        broken = True

    for body in bodies:
        flag = " "
        if body.rstrip().endswith(" 0") or "') 0" in body:
            flag = "!"
            broken = True
        print(f"  {flag} |{body}|")

    print("  VERDICT:", "CORRUPTS" if broken else "clean")
    return broken


def main() -> None:
    print("=" * 78)
    print("BASELINE (verified clean output of the date rewriter)")
    print("=" * 78)
    for body in BASELINE:
        print(f"  |{body}|")

    print("\n" + "=" * 78)
    print("RUNNING EACH DOWNSTREAM PASS IN ISOLATION")
    print("=" * 78)

    