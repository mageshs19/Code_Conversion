from __future__ import annotations

import re

from idms_db2_phase2.transformers.cobol_transformer_line_utils import (
    CobolTransformerLineUtils,
)
from patterns.cobol_patterns import PROGRAM_ID_PATTERN


class CobolProgramIdTransformer:
    """
    Handles target PROGRAM-ID replacement and final PROGRAM-ID period cleanup.
    """

    def __init__(
        self,
        line_utils: CobolTransformerLineUtils | None = None,
    ) -> None:
        self.line_utils = line_utils or CobolTransformerLineUtils()

    def program_id_replacement(
        self,
        *,
        original_line: str,
        logical_line: str,
        target_program_id: str,
    ) -> str | None:
        if not target_program_id:
            return None

        if not PROGRAM_ID_PATTERN.search(logical_line):
            return None

        program_id = str(target_program_id or "").strip().upper()

        if not program_id:
            return None

        replacement_body = f"PROGRAM-ID. {program_id}."

        return self.line_utils.replace_logical_body(
            original_line=original_line,
            replacement_body=replacement_body,
        )

    def fix_program_id_period(
        self,
        *,
        text: str,
        target_program_id: str,
    ) -> str:
        program_id = str(target_program_id or "").strip().upper()

        if program_id:
            pattern = re.compile(
                rf"PROGRAM-ID\.\s*{re.escape(program_id)}\.?",
                flags=re.IGNORECASE,
            )

            return pattern.sub(
                f"PROGRAM-ID. {program_id}.",
                text,
                count=1,
            )

        return re.sub(
            r"(PROGRAM-ID\.\s*[A-Z0-9-]+)\s*$",
            r"\1.",
            text,
            count=1,
            flags=re.IGNORECASE | re.MULTILINE,
        )