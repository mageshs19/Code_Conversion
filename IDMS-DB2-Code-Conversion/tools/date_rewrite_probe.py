# LOCATION: tools/date_rewrite_probe.py
# ACTION: CREATE NEW FILE

"""Runs ONLY the DB2 date rewriter and verifies column geometry.

Three attempts at fixing a mangled condition produced byte-identical
output, which means the rewriter is either not running or not the cause.
This probe answers that question directly: it feeds the exact VMDZ7200
condition to the rewriter alone, with no pipeline around it, and checks
every emitted record.

    $env:PYTHONPATH = "src;."
    python tools\date_rewrite_probe.py

Exit 0: the rewriter is clean, the defect is downstream.
Exit 1: the rewriter is the culprit.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

for _candidate in (PROJECT_ROOT, SRC_DIR):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

from idms_db2_phase2.composers.db2_date_comparison_rewriter import (  # noqa: E402
    Db2DateComparisonRewriter,
)

LINE_WIDTH = 80
BODY_START = 7
BODY_END = 72


def fixed(seq: str, body: str, right: str) -> str:
    return f"{seq} {body.ljust(65)}{right}"


PROGRAM = [
    fixed("001750", " PROCEDURE DIVISION.", "01750000"),
    fixed("002290", " BEHANDELING.", "02290000"),
    fixed("002110", "     IF (DA-CPTAFS-479BFAS OF DCLDZBFASTV < DA-ARCH-YMD", "02110000"),
    fixed("002120", "        AND DA-CPTAFS-479BFAS OF DCLDZBFASTV NOT = '00000000') OR", "02120000"),
    fixed("002130", "        (DA-CRFMAS-479BFAS OF DCLDZBFASTV < DA-ARCH-YMD AND", "02130000"),
    fixed("002140", "        DA-CPTAFS-479BFAS OF DCLDZBFASTV = '00000000')", "02140000"),
    fixed("002150", "        ADD 1 TO WS-TELLER", "02150000"),
    fixed("002160", "     END-IF.", "02160000"),
]


def main() -> None:
    rewriter = Db2DateComparisonRewriter()

    print("=" * 78)
    print("MODULE :", Db2DateComparisonRewriter.__module__)
    print("FILE   :", sys.modules[Db2DateComparisonRewriter.__module__].__file__)
    print("SLICING:", hasattr(rewriter, "_is_fixed_record"))
    print("=" * 78)

    output = rewriter.rewrite_date_comparisons(list(PROGRAM))

    problems: list[str] = []

    print("\nEMITTED RECORDS")
    print("-" * 78)

    for line in output:
        marker = " "
        # A GENERATED line is a plain body with no sequence area; the
        # fixed-format composer numbers it later. Only a line that
        # already carries a left sequence must be a full 80-column
        # record.
        carries_sequence = len(line) >= BODY_START and line[:6].isdigit()

        if carries_sequence and len(line) != LINE_WIDTH:
            marker = "!"
            problems.append(f"width {len(line)}: {line!r}")
        elif line[:6].isdigit() and not line[BODY_END:LINE_WIDTH].isdigit():
            marker = "!"
            problems.append(f"right sequence moved: {line!r}")

        body = line[BODY_START:BODY_END].rstrip() if len(line) >= BODY_END else line
        print(f"{marker} |{body}|")

    print("-" * 78)
    print("\nDIAGNOSTICS")
    for message in rewriter.messages:
        print(" -", message)

    print("\nRESULT")
    if problems:
        print("  REWRITER IS THE CULPRIT")
        for problem in problems:
            print("   ", problem)
        raise SystemExit(1)

    print("  Rewriter output is clean. The defect is in a LATER pass.")
    raise SystemExit(0)


if __name__ == "__main__":
    main()