from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.idms_patterns import (
    ERASE_PATTERN,
    FIND_CURRENT_PATTERN,
    FIND_FIRST_PATTERN,
    MODIFY_PATTERN,
    OBTAIN_CALC_PATTERN,
    OBTAIN_CALC_REVERSED_PATTERN,
    OBTAIN_FIRST_NEXT_PATTERN,
    ON_DB_REC_NOT_FOUND_PATTERN,
    STORE_PATTERN,
)
from rules.idms_transformer_messages import (
    CONVERTED_FIND_FIRST_TEMPLATE,
    CONVERTED_OBTAIN_FIRST_TEMPLATE,
    CONVERTED_OBTAIN_NEXT_TEMPLATE,
    DIRECT_UPDATE_COMPOSITE_KEY,
    FIND_FIRST_OUTSIDE_PROCEDURE_TEMPLATE,
    OBTAIN_CALC_OUTSIDE_PROCEDURE_TEMPLATE,
    OBTAIN_OUTSIDE_PROCEDURE_TEMPLATE,
    OPERATION_ERASE,
    OPERATION_MODIFY,
    OPERATION_STORE,
    PERFORM_FETCH_CURSOR_TEMPLATE,
    PERFORM_OPEN_CURSOR_TEMPLATE,
    REMOVED_FIND_CURRENT_TEMPLATE,
    REMOVED_OBTAIN_CALC_SELECT_TEMPLATE,
    STORE_MODIFY_ERASE_OUTSIDE_PROCEDURE_TEMPLATE,
)
from rules.idms_transformer_rules import (
    CONTINUE_STATEMENT,
    OBTAIN_FIRST_KEYWORD,
    PROCEDURE_DIVISION_NAME,
    SQLCODE_100_CONTINUE_BODY,
    SQLCODE_100_IF_CLOSE,
    SQLCODE_100_IF_OPEN,
)


class DataStatementConverterMixin:
    """Converts IDMS data-access statements to DB2/cursor COBOL."""

    def _convert_on_db_rec_not_found(self, stripped_line):
        match = ON_DB_REC_NOT_FOUND_PATTERN.match(stripped_line)
        if not match:
            return None

        statement = str(match.group("statement") or "").strip()

        if not statement:
            return [SQLCODE_100_IF_OPEN, SQLCODE_100_CONTINUE_BODY, SQLCODE_100_IF_CLOSE]

        return [SQLCODE_100_IF_OPEN, f"   {statement}", SQLCODE_100_IF_CLOSE]

    def _convert_obtain_calc(
        self, upper, stripped_line, current_division, sql_error_paragraph
    ):
        match = OBTAIN_CALC_PATTERN.search(upper) or (
            OBTAIN_CALC_REVERSED_PATTERN.search(upper)
        )
        if not match:
            return None

        record = NameNormalizer.normalize(match.group("record"))
        cobol_record = NameNormalizer.to_cobol(record)

        if current_division != PROCEDURE_DIVISION_NAME:
            return [
                OBTAIN_CALC_OUTSIDE_PROCEDURE_TEMPLATE.format(line=stripped_line)
            ]

        if not self.table_name_resolver.table_for_record(record):
            return self._keep_and_comment_unmapped(
                record=record, stripped_line=stripped_line
            )

        return [
            REMOVED_OBTAIN_CALC_SELECT_TEMPLATE.format(record=cobol_record),
            DIRECT_UPDATE_COMPOSITE_KEY,
            CONTINUE_STATEMENT,
        ]

    def _convert_obtain_first_next(self, upper, stripped_line, current_division):
        match = OBTAIN_FIRST_NEXT_PATTERN.search(upper)
        if not match:
            return None, ""

        record = NameNormalizer.normalize(match.group("record"))
        set_name = NameNormalizer.normalize(match.group("set"))

        if current_division != PROCEDURE_DIVISION_NAME:
            return [OBTAIN_OUTSIDE_PROCEDURE_TEMPLATE.format(line=stripped_line)], ""

        cursor_name = self.cursor_name_resolver.cursor_name_from_table(
            self.table_name_resolver.table_for_record(record)
        )

        if OBTAIN_FIRST_KEYWORD in upper:
            return [
                CONVERTED_OBTAIN_FIRST_TEMPLATE.format(
                    record=record, set_name=set_name
                ),
                PERFORM_OPEN_CURSOR_TEMPLATE.format(cursor=cursor_name),
                PERFORM_FETCH_CURSOR_TEMPLATE.format(cursor=cursor_name),
            ], set_name

        return [
            CONVERTED_OBTAIN_NEXT_TEMPLATE.format(record=record, set_name=set_name),
            PERFORM_FETCH_CURSOR_TEMPLATE.format(cursor=cursor_name),
        ], set_name

    def _convert_find_current(self, upper, stripped_line, current_division):
        if not FIND_CURRENT_PATTERN.search(upper):
            return None
        return self._removed_idms_executable_lines(
            message=REMOVED_FIND_CURRENT_TEMPLATE.format(line=stripped_line),
            current_division=current_division,
        )

    def _convert_find_first(self, upper, stripped_line, current_division):
        match = FIND_FIRST_PATTERN.search(upper)
        if not match:
            return None, ""

        record = NameNormalizer.normalize(match.group("record"))
        set_name = NameNormalizer.normalize(match.group("set"))

        if current_division != PROCEDURE_DIVISION_NAME:
            return [
                FIND_FIRST_OUTSIDE_PROCEDURE_TEMPLATE.format(line=stripped_line)
            ], ""

        table = self.table_name_resolver.table_for_record(record)
        cursor_name = self.cursor_name_resolver.cursor_name_from_table(table)

        return [
            CONVERTED_FIND_FIRST_TEMPLATE.format(record=record, set_name=set_name),
            PERFORM_OPEN_CURSOR_TEMPLATE.format(cursor=cursor_name),
            PERFORM_FETCH_CURSOR_TEMPLATE.format(cursor=cursor_name),
        ], set_name

    def _convert_store_modify_erase(
        self, upper, stripped_line, current_division, sql_error_paragraph
    ):
        for pattern, operation_name, generator_method in [
            (STORE_PATTERN, OPERATION_STORE, self.sql_generator.insert),
            (MODIFY_PATTERN, OPERATION_MODIFY, self.sql_generator.update),
            (ERASE_PATTERN, OPERATION_ERASE, self.sql_generator.delete),
        ]:
            match = pattern.search(upper)
            if not match:
                continue

            record = NameNormalizer.normalize(match.group("record"))

            if current_division != PROCEDURE_DIVISION_NAME:
                return [
                    STORE_MODIFY_ERASE_OUTSIDE_PROCEDURE_TEMPLATE.format(
                        operation=operation_name, line=stripped_line
                    )
                ]

            if not self.table_name_resolver.table_for_record(record):
                return self._keep_and_comment_unmapped(
                    record=record, stripped_line=stripped_line
                )

            return generator_method(record)

        return None