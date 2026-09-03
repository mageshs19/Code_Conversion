from __future__ import annotations

from pathlib import Path

from idms_db2_phase2.testing.retrieval.retrieval_environment import (
    bootstrap_sys_path,
)

SRC_DIR, PROJECT_ROOT = bootstrap_sys_path(Path(__file__))

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
from rules.retrieval_runner_messages import (  # noqa: E402
    BATCH_OUTPUT_FOLDER_TEMPLATE,
    BATCH_PROGRAM_COUNT_TEMPLATE,
    BATCH_PROGRAM_FOLDER_TEMPLATE,
    HEADER_RETRIEVAL_BATCH_SUMMARY,
    RULE_RETRIEVAL_BATCH_SUMMARY,
)
from rules.retrieval_runner_rules import RETRIEVAL_LOGGER_NAME  # noqa: E402

OUTPUT_DIR = DEFAULT_RETRIEVAL_OUTPUT_DIR

__all__ = [
    "resolve_target_program_id",
    "validate_inputs",
    "load_shared_inputs",
    "convert_one_program",
    "run_conversion",
]


def run_conversion() -> None:
    validate_inputs()

    logger = LoggerFactory.create_logger(
        name=RETRIEVAL_LOGGER_NAME,
        logs_dir=LOGS_DIR,
    )

    sheet_rows, dclgen_columns, copybook_fields, diagnostics = load_shared_inputs(
        logger
    )

    program_files = selected_program_paths()

    print("")
    print(HEADER_RETRIEVAL_BATCH_SUMMARY)
    print(RULE_RETRIEVAL_BATCH_SUMMARY)
    print(BATCH_PROGRAM_FOLDER_TEMPLATE.format(value=DEFAULT_RETRIEVAL_PROGRAM_DIR))
    print(BATCH_PROGRAM_COUNT_TEMPLATE.format(value=len(program_files)))
    print(BATCH_OUTPUT_FOLDER_TEMPLATE.format(value=OUTPUT_DIR))

    for program_path in program_files:
        convert_one_program(
            program_path=program_path,
            sheet_rows=sheet_rows,
            dclgen_columns=dclgen_columns,
            copybook_fields=copybook_fields,
            shared_diagnostics=diagnostics,
            output_dir=OUTPUT_DIR,
            project_root=PROJECT_ROOT,
            src_dir=SRC_DIR,
            logger=logger,
        )


if __name__ == "__main__":
    run_conversion()