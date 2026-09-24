# LOCATION: tools/reflow_probe.py
# ACTION: REPLACE ENTIRE FILE

"""Feeds the real VMDZ7200 condition to CobolAreaAlignmentReflow alone.

    $env:PYTHONPATH = "src;."
    python tools\\reflow_probe.py

A '!' on any emitted body names the reflow as the source of the stray
'0' and shows exactly which input pair triggers it.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for _path in (ROOT, ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from idms_db2_phase2.services.cobol_area_alignment_classifier import (  # noqa: E402
    CobolAreaAlignmentClassifier,
)
from idms_db2_phase2.services.cobol_area_alignment_reflow import (  # noqa: E402
    CobolAreaAlignmentReflow,
)
from idms_db2_phase2.services.fixed_format_line_service import (  # noqa: E402
    FixedFormatLineService,
)

QUOTE = chr(39)
ZERO8 = QUOTE + "00000000" + QUOTE
AREA_B = "    "


def fixed(seq: str, body: str, right: str) -> str:
    return seq + " " + body.ljust(65) + right


L1 = fixed("002110", "     IF (HELP-DA-CPTAFS-479BFAS < DA-ARCH-YMD", "02110000")
L2 = fixed("002120", "        AND HELP-DA-CPTAFS-479BFAS NOT = " + ZERO8 + ") OR", "02120000")
L3 = fixed("002130", "        (HELP-DA-CRFMAS-479BFAS < DA-ARCH-YMD AND", "02130000")
L4 = fixed("002140", "        HELP-DA-CPTAFS-479BFAS = " + ZERO8 + ")", "02140000")


def body_of(line: str) -> str:
    return line[7:72].rstrip() if len(line) >= 72 else str(line)


def main() -> None:
    fixed_format = FixedFormatLineService()

    reflow = CobolAreaAlignmentReflow(
        fixed_format=fixed_format,
        classifier=CobolAreaAlignmentClassifier(),
    )

    print("INPUT")
    for line in (L1, L2, L3, L4):
        print("   |" + body_of(line) + "|")

    print("\nlogical() readback")
    for line in (L1, L2, L3, L4):
        print("   " + repr(fixed_format.logical(line)))

    for name, first, second in (
        ("L1 + L2", L1, L2),
        ("L2 + L3", L2, L3),
        ("L3 + L4", L3, L4),
        ("L4 + END-IF", L4, fixed("002160", "     END-IF.", "02160000")),
    ):
        print("\n--- " + name)

        try:
            out = reflow.try_reflow_with_next_line(
                current_line=first,
                next_line=second,
                first_indent=AREA_B,
            )
        except Exception as exc:  # noqa: BLE001
            print("    RAISED:", type(exc).__name__, exc)
            continue

        if not out:
            print("    (no reflow - pair left alone)")
            continue

        print("    reflowed into", len(out), "line(s)")

        for line in out:
            body = body_of(line)
            flag = "!" if body.rstrip().endswith(" 0") else " "
            print("  " + flag + " |" + body + "|  len=" + str(len(line)))


if __name__ == "__main__":
    main()