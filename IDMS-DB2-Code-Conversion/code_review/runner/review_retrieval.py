"""Convert every retrieval program, then code review each generated file.

Reuses the existing retrieval conversion pipeline unchanged. The converted
text is reviewed straight from the file that was just written, so each
program is always matched with its own output.

    set PYTHONPATH=src
    python code_review\\runner\\review_retrieval.py
    python code_review\\runner\\review_retrieval.py --quiet

Exit codes: 0 accepted, 1 rejected, 2 error.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Path bootstrap. Must run before any project or code_review import.
# --------------------------------------------------------------------------
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

for _candidate in (PROJECT_ROOT, SRC_DIR):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))
# --------------------------------------------------------------------------

import argparse  # noqa: E402

from code_review.engine.context import KIND_RETRIEVAL, ReviewContext  # noqa: E402
from code_review.engine.reviewer import Reviewer, blockers, is_accepted  # noqa: E402
from code_review.report import csv_writer, text_writer  # noqa: E402
from code_review.report.text_writer import render  # noqa: E402
from code_review.runner._bootstrap import (  # noqa: E402
    EXIT_ACCEPTED,
    EXIT_ERROR,
    EXIT_REJECTED,
    REPORT_DIR,
    read_text,
    stamp,
)

from config.path_settings import (  # noqa: E402
    DEFAULT_RETRIEVAL_OUTPUT_DIR,
    DEFAULT_RETRIEVAL_PROGRAM_DIR,
    LOGS_DIR,
)
from idms_db2_phase2.infrastructure.logger_factory import (  # noqa: E402
    LoggerFactory,
)
from idms_db2_phase2.testing.retrieval.retrieval_input_loader import (  # noqa: E402
    load_shared_inputs,
)
from idms_db2_phase2.testing.retrieval.retrieval_input_selector import (  # noqa: E402
    selected_program_paths,
    validate_inputs,
)
from idms_db2_phase2.testing.retrieval.retrieval_program_converter import (  # noqa: E402
    convert_one_program,
    resolve_target_program_id,
)

LOGGER_NAME = "idms_db2_retrieval_code_review"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert retrieval programs, then code review the output."
    )
    parser.add_argument(
        "--report",
        default=str(REPORT_DIR),
        help="folder to write the reports into",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="print one summary line per program instead of the full report",
    )
    return parser.parse_args()


def build_context(
    program_path: Path,
    output_path: Path,
    sheet_rows: list,
    dclgen_columns: list,
    copybook_fields: list,
) -> ReviewContext:
    source_text = read_text(program_path)
    return ReviewContext(
        program_name=program_path.stem,
        program_kind=KIND_RETRIEVAL,
        target_program_id=resolve_target_program_id(source_text),
        source_file=Path(output_path).name,
        converted_cobol=read_text(output_path),
        source_cobol=source_text,
        sheet_mapping_rows=sheet_rows,
        dclgen_columns=dclgen_columns,
        copybook_fields=copybook_fields,
    )


def run() -> int:
    args = parse_arguments()

    report_dir = Path(args.report)
    report_dir.mkdir(parents=True, exist_ok=True)

    validate_inputs()

    logger = LoggerFactory.create_logger(name=LOGGER_NAME, logs_dir=LOGS_DIR)

    sheet_rows, dclgen_columns, copybook_fields, diagnostics = load_shared_inputs(
        logger
    )

    programs = selected_program_paths()
    if not programs:
        raise FileNotFoundError(
            f"No retrieval programs found in: {DEFAULT_RETRIEVAL_PROGRAM_DIR}"
        )

    reviewer = Reviewer()
    when = stamp()
    results = []
    failed_conversions: list[str] = []

    print("")
    print("Retrieval Code Review")
    print("-" * 74)
    print(f"Program Folder : {DEFAULT_RETRIEVAL_PROGRAM_DIR}")
    print(f"Program Count  : {len(programs)}")
    print(f"Output Folder  : {DEFAULT_RETRIEVAL_OUTPUT_DIR}")
    print(f"Report Folder  : {report_dir}")
    print("")

    for program_path in programs:
        try:
            output_path = convert_one_program(
                program_path=program_path,
                sheet_rows=sheet_rows,
                dclgen_columns=dclgen_columns,
                copybook_fields=copybook_fields,
                shared_diagnostics=diagnostics,
                output_dir=DEFAULT_RETRIEVAL_OUTPUT_DIR,
                project_root=PROJECT_ROOT,
                src_dir=SRC_DIR,
                logger=logger,
            )
        except Exception as exc:  # noqa: BLE001
            message = f"Conversion failed for {program_path.name}: {exc}"
            print(f"ERROR: {message}")
            logger.exception(message)
            failed_conversions.append(program_path.name)
            continue

        context = build_context(
            program_path=program_path,
            output_path=Path(output_path),
            sheet_rows=sheet_rows,
            dclgen_columns=dclgen_columns,
            copybook_fields=copybook_fields,
        )

        result = reviewer.review(context)
        results.append(result)

        stem = f"{program_path.stem}_{when}"
        text_writer.write(result, report_dir, stem)
        csv_writer.write(result, report_dir, stem)

        if args.quiet:
            verdict = "ACCEPTED" if is_accepted(result) else "REJECTED"
            failing = ", ".join(c.check_id for c in blockers(result))
            suffix = f"  blocking: {failing}" if failing else ""
            print(f"{verdict:<9} {program_path.stem}{suffix}")
        else:
            print(render(result))

    if len(results) > 1:
        csv_writer.write_summary(results, report_dir, f"summary_retrieval_{when}")

    accepted = sum(1 for item in results if is_accepted(item))
    rejected = len(results) - accepted

    print("-" * 74)
    print(f"Reviewed : {len(results)}    Accepted : {accepted}    Rejected : {rejected}")
    if failed_conversions:
        print(f"Conversion failed : {', '.join(failed_conversions)}")
    print(f"Reports written to: {report_dir}")
    print("")

    if failed_conversions:
        return EXIT_ERROR
    return EXIT_ACCEPTED if rejected == 0 else EXIT_REJECTED


def main() -> None:
    try:
        raise SystemExit(run())
    except SystemExit:
        raise
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(EXIT_ERROR)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        raise SystemExit(EXIT_ERROR)


if __name__ == "__main__":
    main()