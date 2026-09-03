from __future__ import annotations

from idms_db2_phase2.services.program_flow_models import DateUsage
from rules.program_flow_rules import DATE_TOKENS


class ProgramDateUsageAnalyzer:
    """
    Detects basic date/time/timestamp usage hints for diagnostics.

    This class does not rewrite COBOL.
    """

    def date_usages(
        self,
        logical_lines: list[tuple[int, str, str]],
    ) -> list[DateUsage]:
        output: list[DateUsage] = []

        for line_number, logical, raw_line in logical_lines:
            upper = logical.upper()

            if not any(token in upper for token in DATE_TOKENS):
                continue

            output.append(
                DateUsage(
                    line_number=line_number,
                    line_text=raw_line,
                    usage_type="date-token",
                )
            )

        return output