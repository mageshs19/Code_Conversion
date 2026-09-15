# LOCATION: src/idms_db2_phase2/testing/batch_execution.py
# ACTION: REPLACE ENTIRE FILE

"""Batch execution entry point: convert and code review in one command.

    set PYTHONPATH=src
    python src\\idms_db2_phase2\\testing\\batch_execution.py
    python src\\idms_db2_phase2\\testing\\batch_execution.py --mode retrieval
    python src\\idms_db2_phase2\\testing\\batch_execution.py --mode update
    python src\\idms_db2_phase2\\testing\\batch_execution.py --no-review
    python src\\idms_db2_phase2\\testing\\batch_execution.py --quiet

Exit codes: 0 all steps passed, 1 a step was rejected, 2 a step errored.

Command line only. Every behaviour lives in
idms_db2_phase2.testing.execution.
"""

from __future__ import annotations

# ---------------------------------------------------------------------
# Path bootstrap.
#
# This block MUST stay above every project import. Running
# "python src\idms_db2_phase2\testing\batch_execution.py" puts only the
# testing folder on sys.path, so without this the first import fails
# with ModuleNotFoundError.
# ---------------------------------------------------------------------
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"

for _candidate in (PROJECT_ROOT, SRC_DIR):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))
# ---------------------------------------------------------------------

import argparse  # noqa: E402

from idms_db2_phase2.testing.execution.orchestrator import (  # noqa: E402
    BatchExecution,
)
from rules.batch_console_rules import (  # noqa: E402
    EXIT_ERROR,
    MODE_ALL,
    MODES,
)

__all__ = ["BatchExecution", "parse_arguments", "main"]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert and code review IDMS COBOL programs in one batch."
        )
    )
    parser.add_argument(
        "--mode",
        choices=list(MODES),
        default=MODE_ALL,
        help="Which program family to process. Default: all.",
    )
    parser.add_argument(
        "--no-review",
        dest="review",
        action="store_false",
        help="Convert only; skip the code review steps.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the animated progress bar.",
    )
    parser.set_defaults(review=True)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    batch = BatchExecution(
        mode=arguments.mode,
        review=arguments.review,
        quiet=arguments.quiet,
    )

    try:
        raise SystemExit(batch.run())
    except SystemExit:
        raise
    except KeyboardInterrupt:
        raise SystemExit(EXIT_ERROR)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        raise SystemExit(EXIT_ERROR)


if __name__ == "__main__":
    main()