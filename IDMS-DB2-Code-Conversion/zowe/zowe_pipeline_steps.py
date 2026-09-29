# LOCATION: zowe/zowe_pipeline_steps.py
# ACTION: CREATE NEW FILE
"""The four executable pipeline steps.

Each returns a StepResult and never raises for a business condition.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from zowe.zowe_console import bullets, warnings
from zowe.zowe_fetcher import ZoweFetcher
from zowe.zowe_rules import (
    MAPPING_MISSING_TEMPLATE,
    STATUS_FAILED,
    STATUS_NOTHING,
    STATUS_OK,
    STATUS_SKIPPED,
    STEP_CONVERT,
    STEP_FETCH,
    STEP_REVIEW,
    STEP_UPLOAD,
)
from zowe.zowe_steps import run_convert, run_review
from zowe.zowe_workspace import (
    count_files,
    mapping_dir,
    output_dir,
    program_dir,
)
from zowe.zowe_writer import upload_converted_folder

COBOL_GLOB = "*.cbl"


@dataclass
class StepResult:
    step: str
    status: str
    seconds: float = 0.0
    code: int = 0

    @property
    def failed(self) -> bool:
        return self.status == STATUS_FAILED


def step_fetch(quiet: bool) -> StepResult:
    started = time.perf_counter()
    result = ZoweFetcher().fetch_all()

    if not quiet:
        bullets(result["diagnostics"])
    warnings(result["warnings"])

    seconds = time.perf_counter() - started
    status = STATUS_OK if result["total_files"] else STATUS_NOTHING
    return StepResult(STEP_FETCH, status, seconds)


def step_convert(quiet: bool) -> StepResult:  # noqa: ARG001
    if count_files(mapping_dir()) == 0:
        print(MAPPING_MISSING_TEMPLATE.format(folder=mapping_dir()))
        return StepResult(STEP_CONVERT, STATUS_SKIPPED)

    if count_files(program_dir()) == 0:
        return StepResult(STEP_CONVERT, STATUS_NOTHING)

    code, seconds = run_convert()
    status = STATUS_OK if code == 0 else STATUS_FAILED
    return StepResult(STEP_CONVERT, status, seconds, code)


def step_review(quiet: bool) -> StepResult:
    if count_files(output_dir(), COBOL_GLOB) == 0:
        return StepResult(STEP_REVIEW, STATUS_NOTHING)

    code, seconds = run_review(quiet)
    # Exit 1 means REJECTED, not broken. The report is still written.
    status = STATUS_OK if code in (0, 1) else STATUS_FAILED
    return StepResult(STEP_REVIEW, status, seconds, code)


def step_upload(quiet: bool) -> StepResult:  # noqa: ARG001
    started = time.perf_counter()

    if count_files(output_dir(), COBOL_GLOB) == 0:
        return StepResult(STEP_UPLOAD, STATUS_NOTHING)

    diagnostics: list[str] = []
    uploaded = upload_converted_folder(output_dir(), diagnostics=diagnostics)
    bullets(diagnostics)

    seconds = time.perf_counter() - started
    status = STATUS_OK if uploaded else STATUS_NOTHING
    return StepResult(STEP_UPLOAD, status, seconds)


STEP_FUNCTIONS = {
    STEP_FETCH: step_fetch,
    STEP_CONVERT: step_convert,
    STEP_REVIEW: step_review,
    STEP_UPLOAD: step_upload,
}