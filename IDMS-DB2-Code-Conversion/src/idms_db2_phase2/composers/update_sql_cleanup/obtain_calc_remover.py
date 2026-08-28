# LOCATION: src/idms_db2_phase2/composers/update_sql_cleanup/obtain_calc_remover.py
# ACTION: CREATE NEW FILE

"""Removes generated OBTAIN CALC SELECT blocks before direct UPDATE."""

from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer


class ObtainCalcRemover:
    def __init__(self, owner, scanner) -> None:
        self.owner = owner
        self.scanner = scanner

    def rewrite(self, text: str) -> str:
        lines = text.splitlines()
        output: list[str] = []
        index = 0
        changed = False

        while index < len(lines):
            logical = self.owner._logical(lines[index])
            match = self.owner.CONVERTED_OBTAIN_CALC_PATTERN.match(logical)

            if not match:
                output.append(lines[index])
                index += 1
                continue

            record = NameNormalizer.normalize(match.group("record"))
            cobol_record = NameNormalizer.to_cobol(record)
            leading = self.owner._leading_spaces(lines[index])
            table = self.owner._table_for_record(record)

            block_end = self.scanner.skip_generated_sql_and_sqlcode(
                lines, index + 1
            )

            if not table:
                output.extend(
                    [
                        f"{leading}*DB2: OBTAIN CALC conversion skipped for "
                        f"{cobol_record}.",
                        f"{leading}*DB2: Missing Sheet Mapping or DCLGEN "
                        f"table metadata.",
                        f"{leading}CONTINUE.",
                    ]
                )
                changed = True
                index = block_end
                continue

            key_columns = self.owner._db2_primary_key_columns(
                record=record,
                table=table,
            )

            if not key_columns:
                output.extend(
                    [
                        f"{leading}*DB2: OBTAIN CALC conversion skipped for "
                        f"{cobol_record}.",
                        f"{leading}*DB2: Missing key column metadata.",
                        f"{leading}CONTINUE.",
                    ]
                )
                changed = True
                index = block_end
                continue

            output.extend(
                [
                    f"{leading}*DB2: Removed OBTAIN CALC SELECT for "
                    f"{cobol_record}.",
                    f"{leading}*DB2: Direct UPDATE will use mapped composite "
                    f"key WHERE clause.",
                    f"{leading}CONTINUE.",
                ]
            )
            changed = True
            index = block_end

        if changed:
            self.owner.messages.append(
                "Update SQL cleanup: removed unnecessary OBTAIN CALC SELECT "
                "before direct UPDATE."
            )

        return "\n".join(output).rstrip() + "\n"