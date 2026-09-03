from __future__ import annotations

from pathlib import Path

from idms_db2_phase2.testing.batch.batch_environment import (
    bootstrap_sys_path,
    env_target_program_id,
)

SRC_DIR, PROJECT_ROOT = bootstrap_sys_path(Path(__file__))

from config.path_settings import DEFAULT_MAPPING_SHEET_DIR, LOGS_DIR  # noqa: E402
from idms_db2_phase2.infrastructure.logger_factory import (  # noqa: E402
    LoggerFactory,
)
from idms_db2_phase2.testing.batch.batch_models import (  # noqa: E402
    BatchMode,
    SharedInputs,
)
from idms_db2_phase2.testing.batch.batch_reporter import (  # noqa: E402
    print_batch_summary,
)
from idms_db2_phase2.testing.batch.batch_validator import (  # noqa: E402
    program_paths_for_mode,
    validate_common_input_folders,
    validate_mode,
)
from idms_db2_phase2.testing.batch.program_converter import (  # noqa: E402
    convert_one_program,
)
from idms_db2_phase2.testing.batch.shared_input_loader import (  # noqa: E402
    load_shared_inputs,
)

__all__ = [
    "BatchMode",
    "SharedInputs",
    "env_target_program_id",
    "program_paths_for_mode",
    "load_shared_inputs",
    "convert_one_program",
    "run_batch",
]


def run_batch(mode: BatchMode) -> None:
    validate_common_input_folders()
    validate_mode(mode)

    logger = LoggerFactory.create_logger(
        name=f"idms_db2_{mode.name.lower()}_conversion",
        logs_dir=LOGS_DIR,
    )

    shared_inputs = load_shared_inputs(logger)
    programs = program_paths_for_mode(mode.name)
    target_program_id = env_target_program_id() or mode.default_target_program_id

    print_batch_summary(
        project_root=PROJECT_ROOT,
        src_dir=SRC_DIR,
        mode=mode,
        mapping_folder=DEFAULT_MAPPING_SHEET_DIR,
        program_count=len(programs),
        target_program_id=target_program_id,
    )

    for program_path in programs:
        convert_one_program(
            mode=mode,
            program_path=program_path,
            shared_inputs=shared_inputs,
            target_program_id=target_program_id,
            logger=logger,
        )