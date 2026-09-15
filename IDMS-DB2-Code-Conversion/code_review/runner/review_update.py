"""Convert every update program, then code review each generated file.

Reuses the existing update conversion pipeline unchanged. The converted
text is reviewed straight from the file that was just written, so each
program is always matched with its own output.

    set PYTHONPATH=src
    python code_review\\runner\\review_update.py
    python code_review\\runner\\review_update.py --quiet

Exit codes: 0 accepted, 1 rejected, 2 error or nothing to convert.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Path bootstrap.
#
# This block MUST stay at the very top, above every code_review and converter
# import. Running "python code_review\runner\review_update.py" puts only
# code_review\runner on sys.path, so without this the package cannot be seen
# and the first import fails with ModuleNotFoundError.
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

from code_review.engine.context import KIND_UPDATE, ReviewContext  # noqa: E402
from code_review.engine.reviewer import (  # noqa: E402
    Reviewer,
    blockers,
    is_accepted,
)
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
from code_review.standards import wording as w  # noqa: E402
from config.path_settings import (  # noqa: E402
    DEFAULT_UPDATE_OUTPUT_DIR,
    DEFAULT_UPDATE_PROGRAM_DIR,
    LOGS_DIR,
)
from idms_db2_phase2.infrastructure.logger_factory import (  # noqa: E402
    LoggerFactory,
)
from idms_db2_phase2.testing.update.update_input_loader import (  # noqa: E402
    load_shared_inputs,
)
from idms_db2_phase2.testing.update.update_input_selector import (  # noqa: E402
    selected_program_paths,
    validate_inputs,
)
from idms_db2_phase2.testing.update.update_program_converter import (  # noqa: E402
    convert_one_program,
    resolve_target_program_id,
)

LOGGER_NAME = "idms_db2_update_code_review"


class NothingToConvert(Exception):
    """The program folder exists but holds no program to convert."""

    def __init__(self, folder: Path, kind_label: str) -> None:
        self.folder = Path(folder)
        self.kind_label = kind_label
        super().__init__(
            w.MSG_NO_PROGRAMS_FOUND.format(kind=kind_label, folder=self.folder)
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert update programs, then code review the output."
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
        program_kind=KIND_UPDATE,
        target_program_id=resolve_target_program_id(source_text),
        source_file=Path(output_path).name,
        converted_cobol=read_text(output_path),
        source_cobol=source_text,
        sheet_mapping_rows=sheet_rows,
        dclgen_columns=dclgen_columns,
        copybook_fields=copybook_fields,
    )


def print_banner(programs: list[Path], report_dir: Path) -> None:
    print("")
    print(w.H_RUN_UPDATE)
    print(w.RULE)
    print(w.MSG_PROGRAM_FOLDER.format(folder=DEFAULT_UPDATE_PROGRAM_DIR))
    print(w.MSG_PROGRAM_COUNT.format(count=len(programs)))
    print(w.MSG_OUTPUT_FOLDER.format(folder=DEFAULT_UPDATE_OUTPUT_DIR))
    print(w.MSG_REPORT_FOLDER.format(folder=report_dir))
    print("")


def print_nothing_to_convert(exc: NothingToConvert) -> int:
    print("")
    print(w.MSG_NO_PROGRAMS_TITLE)
    print(w.RULE)
    print(w.MSG_NO_PROGRAMS_FOUND.format(
        kind=exc.kind_label, folder=exc.folder,
    ))
    print("")
    print(w.MSG_NO_PROGRAMS_HINT)
    print("")
    return EXIT_ERROR


def run() -> int:
    args = parse_arguments()

    report_dir = Path(args.report)
    report_dir.mkdir(parents=True, exist_ok=True)

    # The update selector takes the output folder. The retrieval one does not.
    validate_inputs(DEFAULT_UPDATE_OUTPUT_DIR)
    logger = LoggerFactory.create_logger(name=LOGGER_NAME, logs_dir=LOGS_DIR)

    sheet_rows, dclgen_columns, copybook_fields, diagnostics = (
        load_shared_inputs(logger)
    )

    programs = selected_program_paths()
    if not programs:
        raise NothingToConvert(
            DEFAULT_UPDATE_PROGRAM_DIR, w.KIND_LABEL_UPDATE,
        )

    reviewer = Reviewer()
    when = stamp()
    results = []
    failed_conversions: list[str] = []

    print_banner(programs, report_dir)

    for program_path in programs:
        try:
            output_path = convert_one_program(
                program_path=program_path,
                sheet_rows=sheet_rows,
                dclgen_columns=dclgen_columns,
                copybook_fields=copybook_fields,
                shared_diagnostics=diagnostics,
                output_dir=DEFAULT_UPDATE_OUTPUT_DIR,
                project_root=PROJECT_ROOT,
                src_dir=SRC_DIR,
                logger=logger,
            )
        except Exception as exc:  # noqa: BLE001
            message = w.MSG_CONVERSION_ERROR.format(
                name=program_path.name, reason=exc,
            )
            print(w.MSG_ERROR.format(message=message))
            logger.exception(message)
            failed_conversions.append(program_path.name)
            continue

        result = reviewer.review(build_context(
            program_path=program_path,
            output_path=Path(output_path),
            sheet_rows=sheet_rows,
            dclgen_columns=dclgen_columns,
            copybook_fields=copybook_fields,
        ))
        results.append(result)

        stem = f"{program_path.stem}_{when}"
        text_writer.write(result, report_dir, stem)
        csv_writer.write(result, report_dir, stem)

        if args.quiet:
            ids = ", ".join(c.check_id for c in blockers(result))
            print(w.MSG_QUIET_LINE.format(
                verdict=w.ACCEPTED if is_accepted(result) else w.REJECTED,
                name=program_path.stem,
                suffix=w.MSG_QUIET_BLOCKING.format(ids=ids) if ids else "",
            ))
        else:
            print(render(result))

    if len(results) > 1:
        csv_writer.write_summary(
            results, report_dir, f"summary_update_{when}",
        )

    accepted = sum(1 for item in results if is_accepted(item))
    rejected = len(results) - accepted

    print(w.RULE)
    print(w.MSG_SUMMARY.format(
        reviewed=len(results), accepted=accepted, rejected=rejected,
    ))
    if failed_conversions:
        print(w.MSG_CONVERSION_FAILED.format(
            names=", ".join(failed_conversions),
        ))
    print(w.MSG_REPORTS_WRITTEN.format(folder=report_dir))
    print("")

    if failed_conversions:
        return EXIT_ERROR
    return EXIT_ACCEPTED if rejected == 0 else EXIT_REJECTED


def main() -> None:
    try:
        raise SystemExit(run())
    except SystemExit:
        raise
    except NothingToConvert as exc:
        raise SystemExit(print_nothing_to_convert(exc))
    except FileNotFoundError as exc:
        print(w.MSG_ERROR.format(message=exc))
        raise SystemExit(EXIT_ERROR)
    except Exception as exc:  # noqa: BLE001
        print(w.MSG_ERROR.format(message=exc))
        raise SystemExit(EXIT_ERROR)


if __name__ == "__main__":
    main()