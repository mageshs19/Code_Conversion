# LOCATION: zowe/zowe_pipeline.py
# ACTION: REPLACE ENTIRE FILE
"""One entry point for the whole Zowe flow.

    python -m zowe.zowe_pipeline init
    python -m zowe.zowe_pipeline show
    python -m zowe.zowe_pipeline plan
    python -m zowe.zowe_pipeline fetch
    python -m zowe.zowe_pipeline convert
    python -m zowe.zowe_pipeline review
    python -m zowe.zowe_pipeline upload
    python -m zowe.zowe_pipeline all
    python -m zowe.zowe_pipeline all --to review
    python -m zowe.zowe_pipeline all --from convert

Every step is independently re-runnable. Exit: 0 ok, 1 nothing, 2 error.
"""

from __future__ import annotations

import argparse
import sys

from zowe.zowe_commands import (
    command_clean,
    command_init,
    command_plan,
    command_show,
)
from zowe.zowe_console import configure_logging, header, logger, summary
from zowe.zowe_pipeline_steps import STEP_FUNCTIONS, StepResult
from zowe.zowe_rules import (
    EXIT_ERROR,
    EXIT_NOTHING,
    EXIT_OK,
    PIPELINE_COMMANDS,
    PIPELINE_STEPS,
    STATUS_FAILED,
    STATUS_NOTHING,
    STATUS_OK,
    STATUS_SKIPPED,
    STEP_ALL,
    STEP_CLEAN,
    STEP_FAILED_TEMPLATE,
    STEP_HEADER_TEMPLATE,
    STEP_INIT,
    STEP_NOTHING_TEMPLATE,
    STEP_OK_TEMPLATE,
    STEP_PLAN,
    STEP_SHOW,
    STEP_SKIPPED_TEMPLATE,
    VERDICT_FAILED_TEMPLATE,
    VERDICT_OK,
)
from zowe.zowe_workspace import ensure_workspace

SKIP_REASON = "precondition not met"


def step_range(from_step: str, to_step: str) -> tuple[str, ...]:
    """A contiguous slice of PIPELINE_STEPS. Blank means open-ended."""
    steps = list(PIPELINE_STEPS)
    start = steps.index(from_step) if from_step else 0
    end = steps.index(to_step) + 1 if to_step else len(steps)

    if start >= end:
        raise ValueError(
            f"--from {from_step or steps[0]} comes after "
            f"--to {to_step or steps[-1]}"
        )
    return tuple(steps[start:end])


def _report(result: StepResult) -> None:
    if result.status == STATUS_OK:
        print(STEP_OK_TEMPLATE.format(step=result.step, seconds=result.seconds))
    elif result.status == STATUS_NOTHING:
        print(STEP_NOTHING_TEMPLATE.format(step=result.step))
    elif result.status == STATUS_SKIPPED:
        print(STEP_SKIPPED_TEMPLATE.format(step=result.step, reason=SKIP_REASON))
    else:
        print(
            STEP_FAILED_TEMPLATE.format(
                step=result.step, code=result.code, seconds=result.seconds
            )
        )


def run_steps(steps: tuple[str, ...], quiet: bool) -> int:
    ensure_workspace()
    results: list[StepResult] = []
    total = len(steps)

    for index, step in enumerate(steps, start=1):
        header(
            STEP_HEADER_TEMPLATE.format(index=index, total=total, step=step.upper())
        )
        result = STEP_FUNCTIONS[step](quiet)
        results.append(result)
        _report(result)

        if result.status == STATUS_FAILED:
            summary(results)
            print("")
            print(VERDICT_FAILED_TEMPLATE.format(step=step))
            return EXIT_ERROR

    summary(results)
    print("")
    print(VERDICT_OK)

    return EXIT_OK if any(r.status == STATUS_OK for r in results) else EXIT_NOTHING


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="zowe.zowe_pipeline",
        description="Fetch, convert, review and upload, all inside zowe/workspace.",
    )
    parser.add_argument("command", choices=PIPELINE_COMMANDS)
    parser.add_argument(
        "--from",
        dest="from_step",
        default="",
        choices=("",) + PIPELINE_STEPS,
        help="first step to run when the command is 'all'",
    )
    parser.add_argument(
        "--to",
        dest="to_step",
        default="",
        choices=("",) + PIPELINE_STEPS,
        help="last step to run when the command is 'all'",
    )
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def run() -> int:
    args = parse_arguments()
    configure_logging(args.verbose)

    if args.command == STEP_INIT:
        return command_init()
    if args.command == STEP_SHOW:
        return command_show()
    if args.command == STEP_PLAN:
        return command_plan()
    if args.command == STEP_CLEAN:
        return command_clean()
    if args.command == STEP_ALL:
        return run_steps(step_range(args.from_step, args.to_step), args.quiet)
    return run_steps((args.command,), args.quiet)


def main() -> None:
    try:
        sys.exit(run())
    except KeyboardInterrupt:
        print("")
        print("Interrupted.")
        sys.exit(EXIT_ERROR)
    except Exception as exc:  # noqa: BLE001
        logger().error("%s", exc)
        print("")
        print(f"ERROR: {exc}")
        sys.exit(EXIT_ERROR)


if __name__ == "__main__":
    main()