# LOCATION: src/idms_db2_phase2/composers/update_sql_cleanup/bare_move_rewriter.py
# ACTION: CREATE NEW FILE

"""Rewrites bare 'MOVE ... TO field' targets before a MODIFY into DB2 host moves."""

from __future__ import annotations

from idms_db2_phase2.composers.update_sql_cleanup.date_move_builder import (
    DateMoveBuilder,
)
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class BareMoveRewriter:
    def __init__(self, owner, scanner, date_builder: DateMoveBuilder) -> None:
        self.owner = owner
        self.scanner = scanner
        self.date_builder = date_builder

    def rewrite(self, text: str) -> str:
        lines = text.splitlines()
        output: list[str] = []
        changed = False

        for index, line in enumerate(lines):
            logical = self.owner._logical(line)
            match = self.owner.MOVE_TO_BARE_FIELD_PATTERN.match(logical)

            if not match:
                output.append(line)
                continue

            target = NameNormalizer.to_cobol(match.group("tgt"))

            if self.owner._is_protected_bare_target(target):
                output.append(line)
                continue

            record = self.scanner.next_modify_record(
                lines, index, max_distance=15
            )
            if not record:
                output.append(line)
                continue

            table = self.owner._table_for_record(record)
            column = self.owner._column_for_source_field(record, target)

            if not table or not column:
                output.append(line)
                continue

            host_key = self.owner._host_reference_key(table, column)
            if not host_key:
                output.append(line)
                continue

            leading = self.owner._leading_spaces(line)
            source_value = match.group("src").strip()

            if self.date_builder.is_db2_date_column(column):
                output.extend(
                    self.date_builder.date_ymd8_to_db2_external_move(
                        source_value=source_value,
                        host_key=host_key,
                        leading=leading,
                    )
                )
            else:
                output.append(f"{leading}MOVE {source_value} TO {host_key}")

            changed = True

        if changed:
            self.owner.messages.append(
                "Update SQL cleanup: resolved bare MOVE target through "
                "Sheet Mapping and DCLGEN."
            )

        return "\n".join(output).rstrip() + "\n"