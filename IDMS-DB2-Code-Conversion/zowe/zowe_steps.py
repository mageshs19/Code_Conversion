# LOCATION: zowe/zowe_steps.py
# ACTION: REPLACE ENTIRE FILE
"""Launches the convert and review runners as subprocesses.

TERMINAL GETS A DIGEST, THE FILE GETS EVERYTHING
================================================
Streaming the child verbatim produced 400 lines for two programs and
printed every message twice, because LoggerFactory attaches a
StreamHandler that echoes what the runner already printed. Nothing is
lost: the transcript path is the last line of the digest, and --verbose
restores full streaming.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from zowe.zowe_console import bullets, row, warnings
from zowe.zowe_rules import (
    CONVERT_RUNNER,
    IDMS_INPUT_DIR_KEY,
    PYTHONPATH_ENTRIES,
    PYTHONPATH_KEY,
    REVIEW_KIND,
    REVIEW_RUNNER,
    UNBUFFERED_KEY,
)
from zowe.zowe_step_output import digest
from zowe.zowe_workspace import output_dir, review_dir, workspace_root

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RUNNER_MISSING_TEMPLATE = "Runner not found: {path}"
TRANSCRIPT_TEMPLATE = "{step}_{stamp}.log"
TRANSCRIPT_STAMP = "%d-%m-%Y_%H%M%S"
CHILD_INDENT = "    "

# urllib3 prints InsecureRequestWarning once per request. The TLS state
# is reported once, as a warning row, by the fetch step instead.
WARNINGS_KEY = "PYTHONWARNINGS"
WARNINGS_VALUE = "ignore::urllib3.exceptions.InsecureRequestWarning"

EXIT_RUNNER_MISSING = 2


# --------------------------------------------------------- environment
def subprocess_environment() -> dict[str, str]:
    """The ONLY contract between the pipeline and a runner.

    IDMS_INPUT_DIR is what makes config/path_settings.py resolve to the
    Zowe workspace instead of the developer default.
    """
    env = dict(os.environ)
    env[IDMS_INPUT_DIR_KEY] = str(workspace_root())
    env[PYTHONPATH_KEY] = os.pathsep.join(
        str(PROJECT_ROOT if entry == "." else PROJECT_ROOT / entry)
        for entry in PYTHONPATH_ENTRIES
    )
    env[UNBUFFERED_KEY] = "1"
    env.setdefault(WARNINGS_KEY, WARNINGS_VALUE)
    return env


# ------------------------------------------------------------ transcript
def _logs_dir() -> Path:
    """Workspace Logs folder. Derived, so zowe_workspace need not export it."""
    return workspace_root() / "Logs"


def _write_transcript(step: str, lines: list[str]) -> Path:
    folder = _logs_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / TRANSCRIPT_TEMPLATE.format(
        step=step, stamp=datetime.now().strftime(TRANSCRIPT_STAMP)
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# --------------------------------------------------------------- digest
def _render_digest(text: str, transcript: Path) -> None:
    facts = digest(text)

    if facts["mapping_rows"]:
        row("Sheet Mapping rows", facts["mapping_rows"])
    if facts["dclgen_columns"]:
        row("DCLGEN columns", facts["dclgen_columns"])
    if facts["copybook_fields"]:
        row("Copybook fields", facts["copybook_fields"])
    if facts["lrf_records"]:
        row("LRF records", facts["lrf_records"])

    if facts["outputs"]:
        row("Programs converted", len(facts["outputs"]))
        bullets(Path(p).name for p in facts["outputs"])

    review = facts["review"]
    if review:
        row(
            "Review",
            f"{review['reviewed']} reviewed, "
            f"{review['accepted']} accepted, {review['rejected']} rejected",
        )

    row("Messages", f"{facts['messages']} ({facts['attention_total']} need attention)")

    if facts["attention"]:
        warnings(facts["attention"])
        hidden = facts["attention_total"] - len(facts["attention"])
        if hidden > 0:
            bullets([f"... {hidden} more in the transcript"])

    if facts["errors"]:
        warnings(facts["errors"])
    if facts["crashed"]:
        warnings(["The runner raised an exception. See the transcript."])

    row("Transcript", transcript)


# ------------------------------------------------------------ execution
def _run(
    command: list[str],
    step: str = "step",
    verbose: bool = False,
) -> tuple[int, float]:
    started = time.perf_counter()
    captured: list[str] = []

    process = subprocess.Popen(
        command,
        cwd=str(PROJECT_ROOT),
        env=subprocess_environment(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    for line in process.stdout:
        stripped = line.rstrip()
        captured.append(stripped)
        if verbose and stripped:
            print(f"{CHILD_INDENT}{stripped}")

    process.wait()
    seconds = time.perf_counter() - started

    transcript = _write_transcript(step, captured)
    if not verbose:
        _render_digest("\n".join(captured), transcript)

    return process.returncode, seconds


def run_convert(verbose: bool = False) -> tuple[int, float]:
    runner = PROJECT_ROOT / CONVERT_RUNNER
    if not runner.is_file():
        print(RUNNER_MISSING_TEMPLATE.format(path=runner))
        return EXIT_RUNNER_MISSING, 0.0

    return _run([sys.executable, str(runner)], step="convert", verbose=verbose)


def run_review(quiet: bool = False, verbose: bool = False) -> tuple[int, float]:
    runner = PROJECT_ROOT / REVIEW_RUNNER
    if not runner.is_file():
        print(RUNNER_MISSING_TEMPLATE.format(path=runner))
        return EXIT_RUNNER_MISSING, 0.0

    command = [
        sys.executable,
        str(runner),
        "--folder",
        str(output_dir()),
        "--kind",
        REVIEW_KIND,
        "--report",
        str(review_dir()),
    ]
    if quiet:
        command.append("--quiet")

    return _run(command, step="review", verbose=verbose)


__all__ = ["subprocess_environment", "run_convert", "run_review"]