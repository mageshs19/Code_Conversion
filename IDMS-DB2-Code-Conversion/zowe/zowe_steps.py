# LOCATION: zowe/zowe_steps.py
# ACTION: REPLACE ENTIRE FILE
"""Runs the converter and the code review as subprocesses.

A subprocess is used deliberately: each runner calls sys.exit and does its
own sys.path bootstrap, so importing them would terminate the pipeline or
corrupt the path.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

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
from zowe.zowe_workspace import (
    PROJECT_ROOT,
    output_dir,
    review_dir,
    workspace_root,
)


def subprocess_environment() -> dict[str, str]:
    """Child environment: workspace as input root, explicit PYTHONPATH."""
    env = dict(os.environ)

    entries = [
        str(PROJECT_ROOT) if entry == "." else str(PROJECT_ROOT / entry)
        for entry in PYTHONPATH_ENTRIES
    ]
    existing = env.get(PYTHONPATH_KEY, "")
    if existing:
        entries.append(existing)

    env[PYTHONPATH_KEY] = os.pathsep.join(entries)
    env[IDMS_INPUT_DIR_KEY] = str(workspace_root())
    env[UNBUFFERED_KEY] = "1"
    return env


def _run(command: list[str]) -> tuple[int, float]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            env=subprocess_environment(),
            timeout=STEP_TIMEOUT_SECONDS,
            check=False,
        )
        code = completed.returncode
    except subprocess.TimeoutExpired:
        code = 2
    return code, time.perf_counter() - started


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
    return _run(command)