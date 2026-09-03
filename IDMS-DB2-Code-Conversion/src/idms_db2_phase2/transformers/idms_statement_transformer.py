from __future__ import annotations

from idms_db2_phase2.transformers.idms_statement.control_statement_converter import (
    ControlStatementConverterMixin,
)
from idms_db2_phase2.transformers.idms_statement.data_statement_converter import (
    DataStatementConverterMixin,
)
from idms_db2_phase2.transformers.idms_statement.transformer_shared_mixin import (
    TransformerSharedMixin,
)


class IdmsStatementTransformer(
    TransformerSharedMixin,
    ControlStatementConverterMixin,
    DataStatementConverterMixin,
):
    """Converts executable IDMS statements to DB2-compatible COBOL.

    Conversion logic only. Regex patterns live in patterns/idms_patterns.py;
    all *DB2: message text lives in rules/idms_transformer_messages.py.

    Feedback-driven rules:
    - OBTAIN CALC does not generate DB2 SELECT for update flow.
    - Direct UPDATE is enough when the WHERE has all composite PK/CALC keys.
    - Original IDMS OBTAIN CALC is still removed from final COBOL.
    - SqlGenerator methods already generate SQLCODE checks where required.
    - This transformer must not add duplicate SQLCODE wrappers.
    """

    def __init__(
        self,
        sql_generator,
        sql_error_generator,
        table_name_resolver,
        cursor_name_resolver,
    ) -> None:
        self.sql_generator = sql_generator
        self.sql_error_generator = sql_error_generator
        self.table_name_resolver = table_name_resolver
        self.cursor_name_resolver = cursor_name_resolver
        self.messages: list[str] = []
        # Collect every record with no DB2 target so a composer can comment
        # the WHOLE record block at record level.
        self.unmapped_records: set[str] = set()

    def transform_line(
        self,
        line: str,
        current_division: str,
        sql_error_paragraph: str,
    ) -> tuple[list[str], str]:
        stripped_line = str(line or "").strip()
        upper = stripped_line.upper()

        if not stripped_line:
            return [line], ""

        for converter in (
            lambda: self._convert_declarative_or_control(upper, stripped_line),
            lambda: self._convert_finish_or_commit(
                upper, stripped_line, current_division
            ),
            lambda: self._convert_bind_ready_connect_disconnect(
                upper, stripped_line, current_division
            ),
            lambda: self._convert_status_abort_perform(
                upper, stripped_line, current_division
            ),
            lambda: self._convert_on_db_rec_not_found(stripped_line),
            lambda: self._convert_obtain_calc(
                upper, stripped_line, current_division, sql_error_paragraph
            ),
            lambda: self._convert_find_current(
                upper, stripped_line, current_division
            ),
        ):
            result = converter()
            if result is not None:
                return result, ""

        # Converters that may also open a cursor set.
        obtain_result, opened_set = self._convert_obtain_first_next(
            upper, stripped_line, current_division
        )
        if obtain_result is not None:
            return obtain_result, opened_set

        find_first_result, opened_set = self._convert_find_first(
            upper, stripped_line, current_division
        )
        if find_first_result is not None:
            return find_first_result, opened_set

        store_result = self._convert_store_modify_erase(
            upper, stripped_line, current_division, sql_error_paragraph
        )
        if store_result is not None:
            return store_result, ""

        return self._replace_idms_condition_tokens(line), ""