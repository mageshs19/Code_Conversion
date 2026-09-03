from __future__ import annotations

from pathlib import Path

from idms_db2_phase2.testing.update.update_environment import bootstrap_sys_path

SRC_DIR, PROJECT_ROOT = bootstrap_sys_path(Path(__file__))

from config.path_settings import (  # noqa: E402
    DEFAULT_UPDATE_OUTPUT_DIR,
    DEFAULT_UPDATE_PROGRAM_DIR,
    LOGS_DIR,
)
from idms_db2_phase2.infrastructure.logger_factory import LoggerFactory  # noqa: E402
from idms_db2_phase2.testing.update.update_input_loader import (  # noqa: E402
    load_shared_inputs,
)
from idms_db2_phase2.testing.update.update_input_selector import (  # noqa: E402
    selected_program_paths,
    validate_inputs,
)
from idms_db2_phase2.testing.update.update_postprocess_pipeline import (  # noqa: E402
    enhance_update_program,
)
from idms_db2_phase2.testing.update.update_program_converter import (  # noqa: E402
    convert_one_program,
    resolve_target_program_id,
)
from rules.update_runner_messages import (  # noqa: E402
    BATCH_OUTPUT_FOLDER_TEMPLATE,
    BATCH_PROGRAM_COUNT_TEMPLATE,
    BATCH_PROGRAM_FOLDER_TEMPLATE,
    HEADER_UPDATE_BATCH_SUMMARY,
    RULE_UPDATE_BATCH_SUMMARY,
)
from rules.update_runner_rules import UPDATE_LOGGER_NAME  # noqa: E402

OUTPUT_DIR = DEFAULT_UPDATE_OUTPUT_DIR

__all__ = [
    "resolve_target_program_id",
    "validate_inputs",
    "load_shared_inputs",
    "convert_one_program",
    "enhance_update_program",
    "run_conversion",
]


def run_conversion() -> None:
    validate_inputs(OUTPUT_DIR)

    logger = LoggerFactory.create_logger(
        name=UPDATE_LOGGER_NAME,
        logs_dir=LOGS_DIR,
    )

    sheet_rows, dclgen_columns, copybook_fields, diagnostics = load_shared_inputs(
        logger
    )

    program_files = selected_program_paths()

    print("")
    print(HEADER_UPDATE_BATCH_SUMMARY)
    print(RULE_UPDATE_BATCH_SUMMARY)
    print(BATCH_PROGRAM_FOLDER_TEMPLATE.format(value=DEFAULT_UPDATE_PROGRAM_DIR))
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