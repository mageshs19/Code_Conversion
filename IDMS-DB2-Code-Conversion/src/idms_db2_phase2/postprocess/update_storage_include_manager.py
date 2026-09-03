from __future__ import annotations

import re

from idms_db2_phase2.postprocess.cobol_update_standard_generator import (
    CobolUpdateStandardGenerator,
)
from idms_db2_phase2.postprocess.storage_include.storage_include_injector import (
    StorageIncludeInjector,
)
from idms_db2_phase2.postprocess.storage_include.storage_ws_injector import (
    StorageWsInjector,
)
from idms_db2_phase2.postprocess.update_postprocess_line_utils import (
    UpdatePostprocessLineUtils,
)
from patterns.update_storage_include_patterns import (
    LEGACY_77_DECLARATION_PATTERN_TEMPLATE,
)
from rules.update_restart_rules import (
    UPDATE_LEGACY_RESTART_WS_NAMES,
    UPDATE_RESTART_DIAGNOSTICS,
)


class UpdateStorageIncludeManager(
    StorageWsInjector,
    StorageIncludeInjector,
):
    """Manages update-program storage and include injection.

    Orchestration + legacy WS removal live here. Working-storage/program-name
    passes and include injection are provided by mixins. All skip messages,
    excluded-include names, and templates live in
    rules/update_storage_include_rules.py.
    """

    def __init__(
        self,
        *,
        generator: CobolUpdateStandardGenerator,
        line_utils: UpdatePostprocessLineUtils,
    ) -> None:
        self.generator = generator
        self.line_utils = line_utils

    def remove_legacy_restart_working_storage(self, cobol_text, diagnostics):
        lines = self.line_utils.lines(cobol_text)
        output: list[str] = []
        removed = False

        legacy_patterns = [
            re.compile(
                LEGACY_77_DECLARATION_PATTERN_TEMPLATE.format(name=re.escape(name)),
                flags=re.IGNORECASE,
            )
            for name in UPDATE_LEGACY_RESTART_WS_NAMES
        ]

        for line in lines:
            logical = self.line_utils.logical(line)
            if any(pattern.match(logical) for pattern in legacy_patterns):
                removed = True
                continue
            output.append(line)

        if removed:
            diagnostics.append(UPDATE_RESTART_DIAGNOSTICS["legacy_ws_removed"])

        return self.line_utils.join(output)