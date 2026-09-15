# LOCATION: src/idms_db2_phase2/testing/pytest_runner.py
# ACTION: CREATE NEW FILE

"""Runs the project's pytest suite and returns structured results.

Design notes
------------
- pytest is invoked as a SUBPROCESS, never imported in-process. A test
  module that mutates global state, monkeypatches a shared service or
  calls sys.exit would otherwise corrupt the running Streamlit session.

- Results are read from pytest's JUnit XML report. That format is part
  of pytest core, so no plugin is added to the project's dependencies,
  and parsing is deterministic rather than scraping console text.

- PYTHONPATH is set explicitly for the child process. The converter
  lives under src/ while rules/, patterns/ and catalogs/ sit at the
  project root, so both entries are required.

- The run is bounded by a timeout. A hanging suite must not hang the UI.

This module contains no Streamlit code and no COBOL knowledge.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from rules.test_runner_rules import (
    ALL_TESTS_LABEL,
    FAILING_OUTCOMES,
    JUNIT_ARG_TEMPLATE,
    KEYWORD_ARG,
    OUTCOME_ERROR,
    OUTCOME_FAILED,
    OUTCOME_PASSED,
    OUTCOME_SKIPPED,
    PYTEST_BASE_ARGS,
    PYTEST_MODULE,
    PYTHONPATH_ENTRIES,
    PYTHONPATH_SEPARATOR_KEY,
    RUN_TIMEOUT_SECONDS,
    TEST_FILE_GLOB,
    TESTS_FOLDER,
    TIMESTAMP_FORMAT,
    VERBOSE_ARG,
)


@dataclass
class TestCaseResult:
    """One pytest test case."""

    module: str
    name: str
    outcome: str
    duration: float
    message: str = ""
    detail: str = ""

    @property
    def is_failure(self) -> bool:
        return self.outcome in FAILING_OUTCOMES


@dataclass
class TestRunResult:
    """The outcome of one pytest invocation."""

    command: str
    exit_code: int
    duration: float
    started_at: str
    cases: list[TestCaseResult] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    error: str = ""

    # -- counters --------------------------------------------------
    @property
    def total(self) -> int:
        return len(self.cases)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.cases if c.outcome == OUTCOME_PASSED)

    @property
    def failed(self) -> int:
        return sum(1 for c in self.cases if c.outcome == OUTCOME_FAILED)

    @property
    def errors(self) -> int:
        return sum(1 for c in self.cases if c.outcome == OUTCOME_ERROR)

    @property
    def skipped(self) -> int:
        return sum(1 for c in self.cases if c.outcome == OUTCOME_SKIPPED)

    @property
    def failing(self) -> list[TestCaseResult]:
        return [c for c in self.cases if c.is_failure]

    @property
    def is_green(self) -> bool:
        return (
            not self.timed_out
            and not self.error
            and self.failed == 0
            and self.errors == 0
        )


class PytestRunner:
    """Discovers and runs the project's pytest suite."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or self._resolve_project_root()

    # =================================================================
    # Discovery
    # =================================================================
    @property
    def tests_dir(self) -> Path:
        return self.project_root / TESTS_FOLDER

    def available_targets(self) -> list[str]:
        """Selectable targets: the whole suite, then each test module."""
        if not self.tests_dir.exists():
            return [ALL_TESTS_LABEL]

        modules = sorted(
            path.name
            for path in self.tests_dir.glob(TEST_FILE_GLOB)
            if path.is_file()
        )
        return [ALL_TESTS_LABEL, *modules]

    def has_tests(self) -> bool:
        return len(self.available_targets()) > 1

    # =================================================================
    # Execution
    # =================================================================
    def run(
        self,
        target: str = ALL_TESTS_LABEL,
        keyword: str = "",
        verbose: bool = False,
    ) -> TestRunResult:
        started = datetime.now()
        report_path = Path(
            tempfile.gettempdir()
        ) / f"pytest_report_{started.strftime('%Y%m%d%H%M%S%f')}.xml"

        command = self._build_command(
            target=target,
            keyword=keyword,
            verbose=verbose,
            report_path=report_path,
        )

        result = TestRunResult(
            command=" ".join(command),
            exit_code=-1,
            duration=0.0,
            started_at=started.strftime(TIMESTAMP_FORMAT),
        )

        try:
            completed = subprocess.run(
                command,
                cwd=str(self.project_root),
                env=self._environment(),
                capture_output=True,
                text=True,
                timeout=RUN_TIMEOUT_SECONDS,
                check=False,
            )
            result.exit_code = completed.returncode
            result.stdout = completed.stdout or ""
            result.stderr = completed.stderr or ""

        except subprocess.TimeoutExpired:
            result.timed_out = True

        except Exception as exc:  # noqa: BLE001
            result.error = str(exc)

        result.duration = (datetime.now() - started).total_seconds()

        if report_path.exists():
            result.cases = self._parse_report(report_path)
            self._discard(report_path)

        return result

    # =================================================================
    # Command and environment
    # =================================================================
    def _build_command(
        self,
        target: str,
        keyword: str,
        verbose: bool,
        report_path: Path,
    ) -> list[str]:
        command = [sys.executable, "-m", PYTEST_MODULE]

        selected = str(target or "").strip()
        if selected and selected != ALL_TESTS_LABEL:
            command.append(str(Path(TESTS_FOLDER) / selected))
        else:
            command.append(TESTS_FOLDER)

        command.extend(PYTEST_BASE_ARGS)

        if verbose:
            command.append(VERBOSE_ARG)

        clean_keyword = str(keyword or "").strip()
        if clean_keyword:
            command.extend([KEYWORD_ARG, clean_keyword])

        command.append(JUNIT_ARG_TEMPLATE.format(path=report_path))
        return command

    def _environment(self) -> dict[str, str]:
        env = dict(os.environ)
        entries = [
            str(self.project_root / entry) if entry != "." else str(self.project_root)
            for entry in PYTHONPATH_ENTRIES
        ]
        existing = env.get(PYTHONPATH_SEPARATOR_KEY, "")
        if existing:
            entries.append(existing)
        env[PYTHONPATH_SEPARATOR_KEY] = os.pathsep.join(entries)
        return env

    # =================================================================
    # Report parsing
    # =================================================================
    def _parse_report(self, report_path: Path) -> list[TestCaseResult]:
        try:
            tree = ElementTree.parse(report_path)
        except ElementTree.ParseError:
            return []

        cases: list[TestCaseResult] = []

        for element in tree.iter("testcase"):
            outcome = OUTCOME_PASSED
            message = ""
            detail = ""

            for child in element:
                tag = child.tag.lower()
                if tag == "failure":
                    outcome = OUTCOME_FAILED
                elif tag == "error":
                    outcome = OUTCOME_ERROR
                elif tag == "skipped":
                    outcome = OUTCOME_SKIPPED
                else:
                    continue

                message = str(child.get("message", "") or "").strip()
                detail = str(child.text or "").strip()
                break

            cases.append(
                TestCaseResult(
                    module=self._module_of(element.get("classname", "")),
                    name=str(element.get("name", "") or ""),
                    outcome=outcome,
                    duration=self._float_of(element.get("time", "0")),
                    message=message,
                    detail=detail,
                )
            )

        return cases

    @staticmethod
    def _module_of(classname: str) -> str:
        """tests.test_reflow.TestClass -> tests.test_reflow"""
        text = str(classname or "").strip()
        if not text:
            return ""
        parts = text.split(".")
        if len(parts) > 1 and parts[-1][:1].isupper():
            return ".".join(parts[:-1])
        return text

    @staticmethod
    def _float_of(value: str) -> float:
        try:
            return round(float(value), 3)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _discard(path: Path) -> None:
        try:
            path.unlink()
        except OSError:
            pass

    # =================================================================
    # Helpers
    # =================================================================
    @staticmethod
    def _resolve_project_root() -> Path:
        # .../src/idms_db2_phase2/testing/pytest_runner.py -> project root
        return Path(__file__).resolve().parents[3]