from __future__ import annotations

from idms_db2_phase2.transformers.cobol_transformer_line_utils import (
    CobolTransformerLineUtils,
)
from rules.cobol_transformer_rules import GENERATED_LINE_PREFIXES


class CobolTransformedLineMerger:
    """
    Merges transformed statement output with original fixed-format style when
    the transformation is a safe one-line token replacement.
    """

    def __init__(
        self,
        line_utils: CobolTransformerLineUtils | None = None,
    ) -> None:
        self.line_utils = line_utils or CobolTransformerLineUtils()

    def merge_transformed_lines_with_original_style(
        self,
        *,
        original_line: str,
        original_logical: str,
        transformed_lines: list[str],
    ) -> list[str]:
        if not transformed_lines:
            return [original_line]

        if len(transformed_lines) == 1:
            transformed = str(transformed_lines[0] or "").strip()

            if self.is_single_line_token_replacement(
                original_logical=original_logical,
                transformed_line=transformed,
            ):
                return [
                    self.line_utils.replace_logical_body(
                        original_line=original_line,
                        replacement_body=transformed,
                    )
                ]

            return [transformed]

        return transformed_lines

    def is_single_line_token_replacement(
        self,
        *,
        original_logical: str,
        transformed_line: str,
    ) -> bool:
        original = str(original_logical or "").strip()
        transformed = str(transformed_line or "").strip()
        transformed_upper = transformed.upper()

        if not original or not transformed:
            return False

        if "SQLCODE = 100" in transformed_upper:
            return True

        if "SQLCODE NOT = 100" in transformed_upper:
            return True

        if "SQLCODE NOT = 0" in transformed_upper:
            return True

        if transformed_upper.startswith(GENERATED_LINE_PREFIXES):
            return False

        if transformed.startswith("*"):
            return False

        return False

    def transformer_changed_line(
        self,
        *,
        original_logical: str,
        transformed_lines: list[str],
    ) -> bool:
        if not transformed_lines:
            return False

        if len(transformed_lines) != 1:
            return True

        transformed = str(transformed_lines[0] or "").strip()
        original = str(original_logical or "").strip()

        return transformed != original