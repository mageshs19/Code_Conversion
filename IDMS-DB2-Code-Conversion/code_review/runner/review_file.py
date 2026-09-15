"""Review a generated DB2 COBOL file, or every .cbl in a folder.

Needs no Sheet Mapping, DCLGEN or Copybook. Checks that require metadata
report SKIPPED instead of failing.

    python code_review\\runner\\review_file.py --path C:\\S\\S-Input\\Output\\Retrieval\\VMDZ4420.cbl
    python code_review\\runner\\review_file.py --folder C:\\S\\S-Input\\Output\\Retrieval
    python code_review\\runner\\review_file.py --folder C:\\S\\S-Input\\Output\\Retrieval --latest
    python code_review\\runner\\review_file.py --path out.cbl --source in.txt --kind UPDATE

Exit codes: 0 accepted, 1 rejected, 2 error or nothing to review.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Path bootstrap. Plain inline code, and it MUST run before any code_review
# import, because "python code_review\runner\review_file.py" puts only
# code_review\runner on sys.path.
# ---------------------------------------------------------------------------
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

for _c in (PROJECT_ROOT, SRC_DIR):
    if str(_c) not in sys.path:
        sys.path.insert(0, str(_c))
# ---------------------------------------------------------------------------

import argparse  # noqa: E402

from code_review.engine.context import (  # noqa: E402
    KIND_RETRIEVAL,
    KIND_UNKNOWN,
    KIND_UPDATE,
    ReviewContext,
)
from code_review.engine.reviewer import (  # noqa: E402
    Reviewer,
    blockers,
    is_accepted,
)
from code_review.report import csv_writer, text_writer  # noqa: E402
from code_review.report.text_writer import render  # noqa: E402
from code_review.runner._bootstrap import (  # noqa: E402
    COBOL_GLOB,
    EXIT_ACCEPTED,
    EXIT_ERROR,
    EXIT_REJECTED,
    REPORT_DIR,
    read_text,
    stamp,
)
from code_review.standards import wording as w  # noqa: E402

VALID_KINDS = (KIND_RETRIEVAL, KIND_UPDATE, KIND_UNKNOWN)


class NothingToReview(Exception):
    """The folder exists but holds no generated .cbl."""

    def __init__(self, folder: Path) -> None:
        self.folder = Path(folder)
        super().__init__(w.MSG_NO_OUTPUT_FOUND.format(folder=self.folder))


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Code review a generated DB2 COBOL file."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--path", help="a single .cbl file to review")
    source.add_argument("--folder", help="a folder of .cbl files to review")
    parser.add_argument(
        "--latest",
        action="store_true",
        help="with --folder, review only the newest file",
    )
    parser.add_argument(
        "--source",
        help="original IDMS COBOL source file, optional",
    )
    parser.add_argument(
        "--kind",
        default=KIND_UNKNOWN,
        help="RETRIEVAL, UPDATE or UNKNOWN (default UNKNOWN)",
    )
    parser.add_argument(
        "--report",
        default=str(REPORT_DIR),
        help="folder to write the reports into",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="print one summary line per file instead of the full report",
    )
    return parser.parse_args()


def resolve_targets(args: argparse.Namespace) -> list[Path]:
    if args.path:
        path = Path(args.path)
        if not path.is_file():
            raise FileNotFoundError(w.MSG_FILE_NOT_FOUND.format(path=path))
        return [path]

    folder = Path(args.folder)
    if not folder.exists():
        raise FileNotFoundError(w.MSG_FOLDER_NOT_FOUND.format(folder=folder))
    if not folder.is_dir():
        raise FileNotFoundError(w.MSG_PATH_NOT_FOLDER.format(folder=folder))

    files = sorted(
        (item for item in folder.glob(COBOL_GLOB) if item.is_file()),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not files:
        raise NothingToReview(folder)

    if args.latest:
        return files[:1]
    return sorted(files, key=lambda item: item.name.lower())


def resolve_kind(value: str) -> str:
    kind = str(value or "").strip().upper()
    return kind if kind in VALID_KINDS else KIND_UNKNOWN


def build_context(cbl_path: Path, kind: str, source_text: str) -> ReviewContext:
    return ReviewContext(
        program_name=cbl_path.stem,
        program_kind=kind,
        target_program_id="",
        source_file=cbl_path.name,
        converted_cobol=read_text(cbl_path),
        source_cobol=source_text,
    )


def print_banner(args, targets: list[Path], kind: str, report_dir: Path) -> None:
    print("")
    print(w.H_RUN_FILE)
    print(w.RULE)
    if args.folder:
        print(w.MSG_REVIEWED_FOLDER.format(folder=Path(args.folder)))
    print(w.MSG_FILE_COUNT.format(count=len(targets)))
    print(w.MSG_PROGRAM_KIND.format(kind=kind))
    print(w.MSG_REPORT_FOLDER.format(folder=report_dir))
    print("")


def print_nothing_to_review(exc: NothingToReview) -> int:
    print("")
    print(w.MSG_NO_OUTPUT_TITLE)
    print(w.RULE)
    print(w.MSG_NO_OUTPUT_FOUND.format(folder=exc.folder))
    print("")
    print(w.MSG_NO_OUTPUT_HINT)
    print("")
    return EXIT_ERROR


def run() -> int:
    args = parse_arguments()

    report_dir = Path(args.report)
    report_dir.mkdir(parents=True, exist_ok=True)

    kind = resolve_kind(args.kind)

    source_text = ""
    if args.source:
        source_path = Path(args.source)
        if not source_path.is_file():
            raise FileNotFoundError(
                w.MSG_SOURCE_NOT_FOUND.format(path=source_path)
            )
        source_text = read_text(source_path)

    targets = resolve_targets(args)

    reviewer = Reviewer()
    when = stamp()
    results = []

    print_banner(args, targets, kind, report_dir)

    for cbl_path in targets:
        result = reviewer.review(build_context(cbl_path, kind, source_text))
        results.append(result)

        stem = f"{cbl_path.stem}_{when}"
        text_writer.write(result, report_dir, stem)
        csv_writer.write(result, report_dir, stem)

        if args.quiet:
            ids = ", ".join(c.check_id for c in blockers(result))
            print(w.MSG_QUIET_LINE.format(
                verdict=w.ACCEPTED if is_accepted(result) else w.REJECTED,
                name=cbl_path.name,
                suffix=w.MSG_QUIET_BLOCKING.format(ids=ids) if ids else "",
            ))
        else:
            print(render(result))

    if len(results) > 1:
        csv_writer.write_summary(results, report_dir, f"summary_{when}")

    accepted = sum(1 for item in results if is_accepted(item))
    rejected = len(results) - accepted

    print(w.RULE)
    print(w.MSG_SUMMARY.format(
        reviewed=len(results), accepted=accepted, rejected=rejected,
    ))
    print(w.MSG_REPORTS_WRITTEN.format(folder=report_dir))
    print("")

    return EXIT_ACCEPTED if rejected == 0 else EXIT_REJECTED


def main() -> None:
    try:
        raise SystemExit(run())
    except SystemExit:
        raise
    except NothingToReview as exc:
        raise SystemExit(print_nothing_to_review(exc))
    except FileNotFoundError as exc:
        print(w.MSG_ERROR.format(message=exc))
        raise SystemExit(EXIT_ERROR)
    except Exception as exc:  # noqa: BLE001
        print(w.MSG_ERROR.format(message=exc))
        raise SystemExit(EXIT_ERROR)


if __name__ == "__main__":
    main()