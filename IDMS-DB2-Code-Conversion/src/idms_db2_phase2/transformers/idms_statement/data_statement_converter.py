# LOCATION: src/idms_db2_phase2/transformers/idms_statement/data_statement_converter.py
# ACTION: REPLACE ENTIRE FILE

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

# Indent applied to the statement lifted into the generated
# IF SQLCODE = 100 guard block.
GUARDED_STATEMENT_INDENT = "    "

NO_OPENED_SET = ""


class DataStatementConverterMixin:
    """Converts IDMS data-access statements to DB2/cursor COBOL.

    NAME HANDLING CONTRACT
    ----------------------
    Two forms of every IDMS name are needed and they must never be mixed:

        *_key      NameNormalizer.normalize()  -> DB2 identifier, underscore
                   separated. Used ONLY for resolver / repository lookups
                   and for the opened_set value returned to the caller,
                   which downstream passes re-normalize.

        *_display  NameNormalizer.to_cobol()   -> IDMS / COBOL spelling,
                   hyphen separated. Used ONLY inside generated *DB2:
                   comment text.

    CORRECTION 1 - IDMS set name emitted as a DB2 identifier
    --------------------------------------------------------
    _convert_obtain_first_next and _convert_find_first passed the
    normalized key straight into the comment template, so an LRF-expanded
    program produced

        *DB2: Converted OBTAIN FIRST VMBFAS WITHIN AR_VMBFRM1.

    for the IDMS set AR-VMBFRM1. An IDMS set is not a DB2 identifier and
    must keep its hyphens. _convert_obtain_calc already did this correctly
    via cobol_record; the other two were never brought in line.

    CORRECTION 2 - hyphenated record names were corrupted too
    ---------------------------------------------------------
    The same defect rendered record VMB-FAR as VMB_FAR. It went unnoticed
    only because the reference program's record, VMBFAS, carries no hyphen.

    CORRECTION 3 - no unmapped-record guard on the cursor paths
    -----------------------------------------------------------
    _convert_obtain_calc and _convert_store_modify_erase both refuse when
    table_for_record() is empty. The two cursor converters did not, so an
    unmapped record resolved to an empty table, then to an empty cursor
    name, and the generated lines read

        PERFORM OPEN-.
        PERFORM FETCH-.

    which the compiler rejects. Both now keep and comment the statement.

    CORRECTION 4 - FIND FIRST declares <record> as OPTIONAL
    -------------------------------------------------------
    FIND_FIRST_PATTERN allows 'FIND FIRST WITHIN <set>', which yields
    record=None -> empty record -> the same broken PERFORM. Guarded.
    """

    #
    # ON DB-REC-NOT-FOUND
    #
    def _convert_on_db_rec_not_found(self, stripped_line):
        match = ON_DB_REC_NOT_FOUND_PATTERN.match(stripped_line)

        if not match:
            return None

        statement = str(match.group("statement") or "").strip()

        if not statement:
            return [
                SQLCODE_100_IF_OPEN,
                SQLCODE_100_CONTINUE_BODY,
                SQLCODE_100_IF_CLOSE,
            ]

        return [
            SQLCODE_100_IF_OPEN,
            f"{GUARDED_STATEMENT_INDENT}{statement}",
            SQLCODE_100_IF_CLOSE,
        ]

    #
    # OBTAIN ... CALC
    #
    def _convert_obtain_calc(
        self,
        upper,
        stripped_line,
        current_division,
        sql_error_paragraph,
    ):
        match = OBTAIN_CALC_PATTERN.search(upper) or (
            OBTAIN_CALC_REVERSED_PATTERN.search(upper)
        )

        if not match:
            return None

        record_key = NameNormalizer.normalize(match.group("record"))
        record_display = NameNormalizer.to_cobol(record_key)

        if current_division != PROCEDURE_DIVISION_NAME:
            return [
                OBTAIN_CALC_OUTSIDE_PROCEDURE_TEMPLATE.format(
                    line=stripped_line
                )
            ]

        if not record_key:
            return self._keep_and_comment_unmapped(
                record=record_key,
                stripped_line=stripped_line,
            )

        if not self.table_name_resolver.table_for_record(record_key):
            return self._keep_and_comment_unmapped(
                record=record_key,
                stripped_line=stripped_line,
            )

        return [
            REMOVED_OBTAIN_CALC_SELECT_TEMPLATE.format(record=record_display),
            DIRECT_UPDATE_COMPOSITE_KEY,
            CONTINUE_STATEMENT,
        ]

    #
    # OBTAIN FIRST / NEXT <record> WITHIN <set>
    #
    def _convert_obtain_first_next(
        self,
        upper,
        stripped_line,
        current_division,
    ):
        match = OBTAIN_FIRST_NEXT_PATTERN.search(upper)

        if not match:
            return None, NO_OPENED_SET

        record_key = NameNormalizer.normalize(match.group("record"))
        set_key = NameNormalizer.normalize(match.group("set"))

        record_display = NameNormalizer.to_cobol(record_key)
        set_display = NameNormalizer.to_cobol(set_key)

        if current_division != PROCEDURE_DIVISION_NAME:
            return [
                OBTAIN_OUTSIDE_PROCEDURE_TEMPLATE.format(line=stripped_line)
            ], NO_OPENED_SET

        cursor_name = self._resolve_cursor_name(record_key)

        if not cursor_name:
            return self._keep_and_comment_unmapped(
                record=record_key,
                stripped_line=stripped_line,
            ), NO_OPENED_SET

        if OBTAIN_FIRST_KEYWORD in upper:
            return [
                CONVERTED_OBTAIN_FIRST_TEMPLATE.format(
                    record=record_display,
                    set_name=set_display,
                ),
                PERFORM_OPEN_CURSOR_TEMPLATE.format(cursor=cursor_name),
                PERFORM_FETCH_CURSOR_TEMPLATE.format(cursor=cursor_name),
            ], set_key

        return [
            CONVERTED_OBTAIN_NEXT_TEMPLATE.format(
                record=record_display,
                set_name=set_display,
            ),
            PERFORM_FETCH_CURSOR_TEMPLATE.format(cursor=cursor_name),
        ], set_key

    #
    # FIND CURRENT
    #
    def _convert_find_current(self, upper, stripped_line, current_division):
        if not FIND_CURRENT_PATTERN.search(upper):
            return None

        return self._removed_idms_executable_lines(
            message=REMOVED_FIND_CURRENT_TEMPLATE.format(line=stripped_line),
            current_division=current_division,
        )

    #
    # FIND FIRST <record> WITHIN <set>
    #
    def _convert_find_first(self, upper, stripped_line, current_division):
        match = FIND_FIRST_PATTERN.search(upper)

        if not match:
            return None, NO_OPENED_SET

        record_key = NameNormalizer.normalize(match.group("record"))
        set_key = NameNormalizer.normalize(match.group("set"))

        record_display = NameNormalizer.to_cobol(record_key)
        set_display = NameNormalizer.to_cobol(set_key)

        if current_division != PROCEDURE_DIVISION_NAME:
            return [
                FIND_FIRST_OUTSIDE_PROCEDURE_TEMPLATE.format(
                    line=stripped_line
                )
            ], NO_OPENED_SET

        cursor_name = self._resolve_cursor_name(record_key)

        if not cursor_name:
            return self._keep_and_comment_unmapped(
                record=record_key,
                stripped_line=stripped_line,
            ), NO_OPENED_SET

        return [
            CONVERTED_FIND_FIRST_TEMPLATE.format(
                record=record_display,
                set_name=set_display,
            ),
            PERFORM_OPEN_CURSOR_TEMPLATE.format(cursor=cursor_name),
            PERFORM_FETCH_CURSOR_TEMPLATE.format(cursor=cursor_name),
        ], set_key

    #
    # STORE / MODIFY / ERASE
    #
    def _convert_store_modify_erase(
        self,
        upper,
        stripped_line,
        current_division,
        sql_error_paragraph,
    ):
        for pattern, operation_name, generator_method in (
            (STORE_PATTERN, OPERATION_STORE, self.sql_generator.insert),
            (MODIFY_PATTERN, OPERATION_MODIFY, self.sql_generator.update),
            (ERASE_PATTERN, OPERATION_ERASE, self.sql_generator.delete),
        ):
            match = pattern.search(upper)

            if not match:
                continue

            record_key = NameNormalizer.normalize(match.group("record"))

            if current_division != PROCEDURE_DIVISION_NAME:
                return [
                    STORE_MODIFY_ERASE_OUTSIDE_PROCEDURE_TEMPLATE.format(
                        operation=operation_name,
                        line=stripped_line,
                    )
                ]

            if not record_key:
                return self._keep_and_comment_unmapped(
                    record=record_key,
                    stripped_line=stripped_line,
                )

            if not self.table_name_resolver.table_for_record(record_key):
                return self._keep_and_comment_unmapped(
                    record=record_key,
                    stripped_line=stripped_line,
                )

            return generator_method(record_key)

        return None

    #
    # Shared cursor resolution
    #
    def _resolve_cursor_name(self, record_key: str) -> str:
        """Cursor name for a record, or '' when anything is unresolved.

        Returning '' is the single signal the two cursor converters use to
        fall back to keep-and-comment. Every intermediate step is checked,
        because an empty table silently produced an empty cursor name and
        the generated PERFORM had no paragraph to call.
        """
        if not record_key:
            return ""

        table_name = self.table_name_resolver.table_for_record(record_key)

        if not table_name:
            return ""

        cursor_name = self.cursor_name_resolver.cursor_name_from_table(
            table_name
        )

        return str(cursor_name or "").strip()


__all__ = ["DataStatementConverterMixin"]