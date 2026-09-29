# LOCATION: zowe/zowe_steps.py
# ACTION: REPLACE the environment and runner-launch section

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from zowe.zowe_rules import (
    CONVERT_RUNNER,
    IDMS_INPUT_DIR_KEY,
    PYTHONPATH_ENTRIES,
    PYTHONPATH_KEY,
    REVIEW_KIND,
    REVIEW_RUNNER,
    RUNNER_MISSING_TEMPLATE,
    STEP_TIMEOUT_SECONDS,
    UNBUFFERED_KEY,
)
from zowe.zowe_workspace import output_dir, review_dir, workspace_root

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# urllib3 prints InsecureRequestWarning once per request. Eight fetches
# produced eight identical blocks in a console the COBOL team reads at a
# glance. The TLS state is reported ONCE, as a warning row, by the fetch
# step instead.
WARNINGS_KEY = "PYTHONWARNINGS"
WARNINGS_VALUE = "ignore::urllib3.exceptions.InsecureRequestWarning"


def subprocess_environment() -> dict[str, str]:
    """The ONLY contract between the pipeline and a runner."""
    env = dict(os.environ)
    env[IDMS_INPUT_DIR_KEY] = str(workspace_root())
    env[PYTHONPATH_KEY] = os.pathsep.join(
        str(PROJECT_ROOT if entry == "." else PROJECT_ROOT / entry)
        for entry in PYTHONPATH_ENTRIES
    )
    env[UNBUFFERED_KEY] = "1"
    env.setdefault(WARNINGS_KEY, WARNINGS_VALUE)
    return env


def _run(command: list[str], indent: str = "    ") -> tuple[int, float]:
    """Run one runner, echoing its output under the step indent."""
    started = time.perf_counter()
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
    try:
        for line in process.stdout:
            stripped = line.rstrip()
            if stripped:
                print(f"{indent}{stripped}")
        process.wait(timeout=STEP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        return 2, time.perf_counter() - started
    return process.returncode, time.perf_counter() - started


def run_convert() -> tuple[int, float]:
    runner = PROJECT_ROOT / CONVERT_RUNNER
    if not runner.is_file():
        print(RUNNER_MISSING_TEMPLATE.format(path=runner))
        return 2, 0.0
    return _run([sys.executable, str(runner)])


def run_review(quiet: bool = False) -> tuple[int, float]:
    runner = PROJECT_ROOT / REVIEW_RUNNER
    if not runner.is_file():
        print(RUNNER_MISSING_TEMPLATE.format(path=runner))
        return 2, 0.0
    command = [
        sys.executable, str(runner),
        "--folder", str(output_dir()),
        "--kind", REVIEW_KIND,
        "--report", str(review_dir()),
    ]
    if quiet:
        command.append("--quiet")
    return _run(command)