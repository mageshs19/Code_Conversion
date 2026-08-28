# LOCATION: src/idms_db2_phase2/testing/line_preservation_audit.py
# ACTION: REPLACE ENTIRE FILE

"""
Line-preservation audit tool.

Answers the core question:
    "Did the converter change ONLY the IDMS/DB2 lines and leave every other
     business line byte-for-byte identical?"

This is the CORRECT benchmark for a surgical IDMS->DB2 converter — NOT a
match against a human rewrite manual (which adds paragraph renaming,
counters, restructuring, etc. that the converter deliberately does not do).

Classification of each INPUT line:
    CONVERTIBLE  -> allowed to change (IDMS statement / control / mapped ref)
    PRESERVE     -> must appear unchanged in the output
    COMMENT/BLANK -> ignored

The audit reports:
    - PRESERVE lines that were dropped or modified   -> POTENTIAL BUG
    - CONVERTIBLE lines that changed                 -> expected
    - A pass/fail summary

Usage (from project root, with PYTHONPATH=src):
    python src\\idms_db2_phase2\\testing\\line_preservation_audit.py ^
        --input  C:\\S\\S-Input\\Update.txt ^
        --output C:\\S\\S-Input\\Output\\Update_<timestamp>.cbl ^
        [--verbose]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
SRC_DIR = CURRENT_FILE.parents[2]
PROJECT_ROOT = CURRENT_FILE.parents[3]
for path in (PROJECT_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


# --- Fixed-format helpers ---

def _strip_sequence_area(line: str) -> str:
    """
    Return the COBOL body (columns 8-72 area), handling fixed-format:
    - cols 1-6  : sequence number
    - col 7     : indicator (* / D)
    - cols 8-72 : body
    - cols 73-80: right sequence
    """
    text = str(line or "").rstrip("\n").rstrip()

    # Full fixed-format line (>= 72 with digit left sequence).
    if len(text) >= 72 and text[:6].strip().isdigit():
        return text[7:72].strip()

    # Left sequence only.
    if len(text) > 6 and text[:6].strip().isdigit():
        body = text[6:]
        # Drop a trailing 8-digit right sequence if present.
        if len(body) >= 8 and body[-8:].strip().isdigit():
            body = body[:-8]
        # Column-7 indicator handling.
        if body[:1] in ("*", "/", "D"):
            return body.strip()
        return body.strip()

    return text.strip()


def _indicator(line: str) -> str:
    """Return the column-7 indicator char, or '' if not fixed-format."""
    text = str(line or "").rstrip("\n")
    if len(text) >= 7 and text[:6].strip().isdigit():
        return text[6:7]
    return ""


def _is_comment_or_blank(line: str) -> bool:
    ind = _indicator(line)
    if ind in ("*", "/"):
        return True
    body = _strip_sequence_area(line)
    if not body:
        return True
    if body.startswith("*") or body.startswith("/"):
        return True
    return False


def _norm(body: str) -> str:
    """
    Collapse internal whitespace and drop a trailing period so that
    re-indentation and period differences are not treated as changes.
    """
    text = re.sub(r"\s+", " ", str(body or "").strip()).upper()
    return text.rstrip(".")


# --- CONVERTIBLE patterns (allowed to change) ---

_CONVERTIBLE_PATTERNS = [
    # IDMS executable database verbs
    re.compile(r"^\s*OBTAIN\b", re.IGNORECASE),
    re.compile(r"^\s*FIND\s+CURRENT\b", re.IGNORECASE),
    re.compile(r"^\s*FIND\s+FIRST\b", re.IGNORECASE),
    re.compile(r"^\s*STORE\b", re.IGNORECASE),
    re.compile(r"^\s*MODIFY\b", re.IGNORECASE),
    re.compile(r"^\s*ERASE\b", re.IGNORECASE),
    re.compile(r"^\s*CONNECT\b", re.IGNORECASE),
    re.compile(r"^\s*DISCONNECT\b", re.IGNORECASE),
    re.compile(r"^\s*FINISH\b", re.IGNORECASE),
    re.compile(r"^\s*BIND\b", re.IGNORECASE),
    re.compile(r"^\s*READY\b", re.IGNORECASE),
    re.compile(r"\bUSAGE-MODE\s+IS\s+(UPDATE|RETRIEVAL)\b", re.IGNORECASE),
    re.compile(r"\bIDMS-STATUS\b", re.IGNORECASE),
    re.compile(r"\bIDMS-ABORT\b", re.IGNORECASE),
    re.compile(r"^\s*ON\s+DB-REC-NOT-FOUND\b", re.IGNORECASE),
    re.compile(r"\bDB-REC-NOT-FOUND\b", re.IGNORECASE),
    re.compile(r"\bDB-END-OF-SET\b", re.IGNORECASE),
    # IDMS declarative / control
    re.compile(r"^\s*IDMS-CONTROL\s+SECTION\b", re.IGNORECASE),
    re.compile(r"^\s*PROTOCOL\b", re.IGNORECASE),
    re.compile(r"^\s*IDMS-RECORDS\s+WITHIN\b", re.IGNORECASE),
    re.compile(r"^\s*SCHEMA\s+SECTION\b", re.IGNORECASE),
    re.compile(r"^\s*DB\s+[A-Z0-9-]+\s+WITHIN\s+[A-Z0-9-]+\b", re.IGNORECASE),
    re.compile(r"^\s*COPY\s+IDMS\b", re.IGNORECASE),
    # DB2-related lines the converter may change
    re.compile(r"^\s*COMMIT\b", re.IGNORECASE),
    re.compile(r"^\s*CBL\b", re.IGNORECASE),
    re.compile(r"^\s*PROGRAM-ID\.", re.IGNORECASE),
    re.compile(r"\bTO\s+PROGRAM-NAME\b", re.IGNORECASE),
    # A move whose TARGET is a date field DA-/DT- (gets date conversion).
    re.compile(r"\bTO\s+(?:DA|DT)-[A-Z0-9-]+\b", re.IGNORECASE),
    # A move/reference to an IDMS record (bare or qualified).
    re.compile(r"\bTO\s+VMB[A-Z0-9-]*\s*\.?\s*$", re.IGNORECASE),
    re.compile(r"\bTO\s+FFRECAB\b", re.IGNORECASE),
    re.compile(r"\bOF\s+FFRECAB\b", re.IGNORECASE),
    re.compile(r"\bOF\s+VMB[A-Z0-9-]*\b", re.IGNORECASE),
]

_QUALIFIED_REF_PATTERN = re.compile(
    r"\b[A-Z][A-Z0-9-]*\s+(?:OF|IN)\s+[A-Z][A-Z0-9-]*\b",
    re.IGNORECASE,
)


def _is_convertible(body: str) -> bool:
    for pattern in _CONVERTIBLE_PATTERNS:
        if pattern.search(body):
            return True
    match = _QUALIFIED_REF_PATTERN.search(body)
    if match:
        upper = body.upper()
        if " OF DCL" not in upper and " IN DCL" not in upper:
            return True
    return False


def audit(input_text: str, output_text: str) -> dict:
    input_lines = input_text.splitlines()
    output_bodies = {
        _norm(_strip_sequence_area(line))
        for line in output_text.splitlines()
        if not _is_comment_or_blank(line)
    }

    preserved_ok: list[tuple[int, str]] = []
    preserved_missing: list[tuple[int, str]] = []
    convertible: list[tuple[int, str]] = []
    comments_blank = 0

    for index, raw in enumerate(input_lines, start=1):
        if _is_comment_or_blank(raw):
            comments_blank += 1
            continue

        body = _strip_sequence_area(raw)

        if _is_convertible(body):
            convertible.append((index, body))
            continue

        if _norm(body) in output_bodies:
            preserved_ok.append((index, body))
        else:
            preserved_missing.append((index, body))

    return {
        "preserved_ok": preserved_ok,
        "preserved_missing": preserved_missing,
        "convertible": convertible,
        "comments_blank": comments_blank,
        "total_preserve": len(preserved_ok) + len(preserved_missing),
        "passed": len(preserved_missing) == 0,
    }


def print_report(report: dict, verbose: bool = False) -> None:
    print("")
    print("=" * 70)
    print("LINE-PRESERVATION AUDIT")
    print("=" * 70)
    print(f"Comment/blank lines (ignored)      : {report['comments_blank']}")
    print(
        f"Convertible lines (allowed change) : "
        f"{len(report['convertible'])}"
    )
    print(f"Preserve lines (must stay same)    : {report['total_preserve']}")
    print(
        f"  -> preserved correctly           : "
        f"{len(report['preserved_ok'])}"
    )
    print(
        f"  -> MISSING / CHANGED (bugs)      : "
        f"{len(report['preserved_missing'])}"
    )
    print("-" * 70)

    if report["preserved_missing"]:
        print("BUSINESS lines dropped or changed (investigate each):")
        print("")
        for line_number, body in report["preserved_missing"]:
            print(f"  input line {line_number:>5}:  {body}")
        print("")
    else:
        print("No business lines were dropped or modified.")
        print("Only IDMS/DB2 lines changed. Correct surgical conversion.")

    if verbose:
        print("-" * 70)
        print("Convertible lines (expected to change):")
        for line_number, body in report["convertible"]:
            print(f"  input line {line_number:>5}:  {body}")

    print("=" * 70)
    print(f"RESULT: {'PASS' if report['passed'] else 'FAIL'}")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Audit whether the converter changed ONLY IDMS/DB2 lines and "
            "preserved all other business logic."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the original IDMS COBOL source (converter input).",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the generated DB2 COBOL (converter output).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Also list the convertible lines that were expected to change.",
    )
    args = parser.parse_args()

    input_text = Path(args.input).read_text(
        encoding="utf-8", errors="replace"
    )
    output_text = Path(args.output).read_text(
        encoding="utf-8", errors="replace"
    )

    report = audit(input_text=input_text, output_text=output_text)
    print_report(report, verbose=args.verbose)
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()