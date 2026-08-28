# LOCATION: src/idms_db2_phase2/composers/update_sql_cleanup/modify_update_rewriter.py
# ACTION: CREATE NEW FILE

"""Rewrites generated MODIFY markers into conservative DB2 UPDATE blocks."""

from __future__ import annotations

from idms_db2_phase2.composers.update_sql_cleanup.composer_patterns import (
    ANY_DCL_DOT_REFERENCE_PATTERN,
    ANY_DCL_OF_REFERENCE_PATTERN,
    MOVE_TO_DCL_DOT_HOST_PATTERN,
    STRING_INTO_DCL_DOT_HOST_PATTERN,
    STRING_INTO_DCL_HOST_PATTERN,
)
from idms_db2_phase2.services.name_normalizer import NameNormalizer

# ADD to the imports at the top of modify_update_rewriter.py:
from rules.update_sql_cleanup_rules import UPDATE_QUERYNO

class ModifyUpdateRewriter:
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
            match = self.owner.CONVERTED_MODIFY_PATTERN.match(logical)

            if not match:
                output.append(lines[index])
                index += 1
                continue

            record = NameNormalizer.normalize(match.group("record"))
            table = self.owner._table_for_record(record)
            key_columns = self.owner._db2_primary_key_columns(record, table)

            changed_columns = self._changed_columns_after_obtain_calc(
                record=record,
                table=table,
                lines=lines,
                modify_index=index,
            )
            update_columns = self._update_columns(
                record=record,
                table=table,
                changed_columns=changed_columns,
            )

            if not table or not key_columns or not update_columns:
                output.append(lines[index])
                index += 1
                continue

            block_end = self.scanner.skip_generated_sql_and_sqlcode(
                lines, index + 1
            )
            output.extend(
                self._conservative_update_block(
                    record=record,
                    table=table,
                    update_columns=update_columns,
                    key_columns=key_columns,
                    leading=self.owner._leading_spaces(lines[index]),
                )
            )
            changed = True
            index = block_end

        if changed:
            self.owner.messages.append(
                "Update SQL cleanup: rewrote MODIFY UPDATE to changed field "
                "plus update audit fields."
            )

        return "\n".join(output).rstrip() + "\n"

    def _conservative_update_block(
        self,
        record: str,
        table: str,
        update_columns: list[str],
        key_columns: list[str],
        leading: str,
    ) -> list[str]:
        lines = [
            f"{leading}*DB2: Converted MODIFY for "
            f"{NameNormalizer.to_cobol(record)}.",
            f"{leading}MOVE 'UPDATE-{NameNormalizer.to_cobol(record)}' "
            f"TO SQL-LOCATION.",
            f"{leading}EXEC SQL",
            f"{leading}   UPDATE {table}",
            f"{leading}   SET",
        ]
        lines.extend(
            self.owner._set_lines(table, update_columns, leading + "      ")
        )
        lines.append(f"{leading}   WHERE")
        lines.extend(
            self.owner._where_lines(table, key_columns, leading + "      ")
        )
        lines.append(f"{leading}   QUERYNO {UPDATE_QUERYNO}")
        lines.append(f"{leading}END-EXEC")

        # Manual-standard SQLCODE handling: EVALUATE SQLCODE.
        lines.append(f"{leading}EVALUATE SQLCODE")
        lines.append(f"{leading}    WHEN 0")
        lines.append(f"{leading}         CONTINUE")
        lines.append(f"{leading}    WHEN OTHER")
        lines.append(
            f"{leading}         DISPLAY 'ERROR ON UPDATE {table}'"
        )
        lines.append(f"{leading}         PERFORM SQLERROR")
        lines.append(f"{leading}END-EVALUATE")
        lines.append(f"{leading}.")

        return lines
    
    def _changed_columns_after_obtain_calc(
        self,
        record: str,
        table: str,
        lines: list[str],
        modify_index: int,
    ) -> list[str]:
        start = self._post_select_scan_start(lines, modify_index)
        return self._changed_columns_in_range(
            record=record,
            table=table,
            lines=lines,
            start=start,
            end=modify_index,
        )

    def _post_select_scan_start(
        self,
        lines: list[str],
        modify_index: int,
    ) -> int:
        search_start = max(0, modify_index - 80)
        latest_boundary = -1

        for index in range(search_start, modify_index):
            logical = self.owner._logical(lines[index])
            upper = logical.upper()

            if self.owner.EXEC_SQL_END_PATTERN.match(logical):
                latest_boundary = index
                continue
            if "REMOVED OBTAIN CALC SELECT" in upper:
                latest_boundary = index
                continue
            if "DIRECT UPDATE WILL USE MAPPED COMPOSITE KEY" in upper:
                latest_boundary = index
                continue

        if latest_boundary >= 0:
            return latest_boundary + 1

        return max(0, modify_index - 20)

    def _changed_columns_in_range(
        self,
        record: str,
        table: str,
        lines: list[str],
        start: int,
        end: int,
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()
        in_string_block = False

        for index in range(start, end):
            logical = self.owner._logical(lines[index])
            upper = logical.upper()

            if upper.startswith("STRING "):
                in_string_block = True

            column = self._changed_column_from_logical(
                record=record,
                table=table,
                logical=logical,
                in_string_block=in_string_block,
            )
            if column and column not in seen:
                seen.add(column)
                output.append(column)

            if upper.startswith("END-STRING"):
                in_string_block = False

        return self.owner._filter_existing_dclgen_columns(table, output)

    def _changed_column_from_logical(
        self,
        record: str,
        table: str,
        logical: str,
        in_string_block: bool = False,
    ) -> str:
        bare_match = self.owner.MOVE_TO_BARE_FIELD_PATTERN.match(logical)
        if bare_match:
            target = NameNormalizer.to_cobol(bare_match.group("tgt"))
            return self.owner._column_for_source_field(record, target)

        of_match = self.owner.MOVE_TO_DCL_HOST_PATTERN.match(logical)
        if of_match:
            return self._column_for_host(
                table=table,
                group=NameNormalizer.normalize(of_match.group("group")),
                host=NameNormalizer.to_cobol(of_match.group("host")),
            )

        dot_match = MOVE_TO_DCL_DOT_HOST_PATTERN.match(logical)
        if dot_match:
            return self._column_for_host(
                table=table,
                group=NameNormalizer.normalize(dot_match.group("group")),
                host=NameNormalizer.to_cobol(dot_match.group("host")),
            )

        string_into_match = STRING_INTO_DCL_HOST_PATTERN.match(logical)
        if string_into_match:
            return self._column_for_host(
                table=table,
                group=NameNormalizer.normalize(
                    string_into_match.group("group")
                ),
                host=NameNormalizer.to_cobol(string_into_match.group("host")),
            )

        string_dot_match = STRING_INTO_DCL_DOT_HOST_PATTERN.match(logical)
        if string_dot_match:
            return self._column_for_host(
                table=table,
                group=NameNormalizer.normalize(
                    string_dot_match.group("group")
                ),
                host=NameNormalizer.to_cobol(string_dot_match.group("host")),
            )

        if in_string_block and "INTO" in logical.upper():
            generic_of_match = ANY_DCL_OF_REFERENCE_PATTERN.search(logical)
            if generic_of_match:
                return self._column_for_host(
                    table=table,
                    group=NameNormalizer.normalize(
                        generic_of_match.group("group")
                    ),
                    host=NameNormalizer.to_cobol(
                        generic_of_match.group("host")
                    ),
                )

            generic_dot_match = ANY_DCL_DOT_REFERENCE_PATTERN.search(logical)
            if generic_dot_match:
                return self._column_for_host(
                    table=table,
                    group=NameNormalizer.normalize(
                        generic_dot_match.group("group")
                    ),
                    host=NameNormalizer.to_cobol(
                        generic_dot_match.group("host")
                    ),
                )

        return ""

    def _column_for_host(
        self,
        table: str,
        group: str,
        host: str,
    ) -> str:
        expected_group = NameNormalizer.normalize(
            self.owner.dclgen_repository.group_for_table(table)
        )
        if group != expected_group:
            return ""

        target_host = NameNormalizer.to_cobol(host)

        for column in self.owner.dclgen_repository.columns_for_table(table):
            current_host = NameNormalizer.to_cobol(
                column.cobol_host_name or column.column_name
            )
            if current_host == target_host:
                return NameNormalizer.normalize(column.column_name)

        return ""

    def _update_columns(
        self,
        record: str,
        table: str,
        changed_columns: list[str],
    ) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()
        key_columns = set(
            self.owner._db2_primary_key_columns(record, table)
        )

        for column in changed_columns:
            normalized = NameNormalizer.normalize(column)
            if not normalized or normalized in key_columns or normalized in seen:
                continue
            seen.add(normalized)
            output.append(normalized)

        for column in self.owner._update_audit_columns(record, table):
            normalized = NameNormalizer.normalize(column)
            if not normalized or normalized in key_columns or normalized in seen:
                continue
            seen.add(normalized)
            output.append(normalized)

        return self.owner._filter_existing_dclgen_columns(table, output)