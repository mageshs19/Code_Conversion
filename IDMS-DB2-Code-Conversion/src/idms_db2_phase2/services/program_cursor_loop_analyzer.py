from __future__ import annotations

from idms_db2_phase2.domain.models import IdmsOperation
from idms_db2_phase2.resolvers.cursor_name_resolver import CursorNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from idms_db2_phase2.services.program_flow_models import CursorLoop
from rules.program_flow_rules import CURSOR_OPERATIONS


class ProgramCursorLoopAnalyzer:
    """
    Builds cursor-loop diagnostics from parsed IDMS operations.

    This class does not inspect or rewrite COBOL text.
    """

    def __init__(
        self,
        cursor_name_resolver: CursorNameResolver | None = None,
    ) -> None:
        self.cursor_name_resolver = cursor_name_resolver or CursorNameResolver()

    def cursor_loops(
        self,
        operations: list[IdmsOperation],
    ) -> list[CursorLoop]:
        output: list[CursorLoop] = []
        cursor_order_by_name: dict[str, int] = {}

        for operation in operations:
            operation_name = str(operation.operation or "").upper()

            if operation_name not in CURSOR_OPERATIONS:
                continue

            record_name = NameNormalizer.normalize(operation.record_name)
            set_name = NameNormalizer.normalize(operation.set_name)

            if not record_name:
                continue

            cursor_name = self.cursor_name_resolver.cursor_name_from_table(record_name)

            if cursor_name not in cursor_order_by_name:
                cursor_order_by_name[cursor_name] = len(cursor_order_by_name) + 1

            paragraph_spec = self.cursor_name_resolver.paragraph_names(
                cursor_order=cursor_order_by_name[cursor_name],
                cursor_name=cursor_name,
            )

            output.append(
                CursorLoop(
                    record_name=record_name,
                    set_name=set_name,
                    operation=operation_name,
                    operation_line=operation.line_number,
                    loop_type="cursor",
                    cursor_name=cursor_name,
                    open_paragraph=paragraph_spec["open"],
                    fetch_paragraph=paragraph_spec["fetch"],
                    close_paragraph=paragraph_spec["close"],
                )
            )

        return output