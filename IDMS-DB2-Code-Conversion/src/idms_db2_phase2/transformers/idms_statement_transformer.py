# LOCATION: src/idms_db2_phase2/transformers/idms_statement_transformer.py
# ACTION: REPLACE ENTIRE FILE

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

# Converter call signatures. The mixins are deliberately left untouched,
# so the dispatcher adapts to them rather than the other way round.
ARITY_LINE = 1          # (stripped_line)
ARITY_UPPER_LINE = 2    # (upper, stripped_line)
ARITY_WITH_DIVISION = 3  # (upper, stripped_line, current_division)
ARITY_WITH_SQL_ERROR = 4  # (upper, stripped_line, division, sql_error_paragraph)

NO_OPENED_SET = ""


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

    CORRECTION 1 - state leaked between programs
    --------------------------------------------
    ConversionComponentFactory builds ONE instance, and the batch runners
    convert every program in the folder inside a single process. Because
    `messages` and `unmapped_records` were only initialised in __init__,
    program 1's unmapped records were still present when program 2 ran,
    and the record-level composer commented records program 2 never
    referenced. reset() now clears per-program state; call it once per
    program, before the first transform_line().

    CORRECTION 2 - an empty result deleted a statement
    --------------------------------------------------
    The dispatcher accepted any non-None result. A converter that returned
    an empty list therefore removed the source line silently. Only a
    NON-EMPTY result now counts as a conversion; anything else falls
    through to the next converter and finally to token replacement, so a
    statement can never disappear without a *DB2: comment explaining it.

    CORRECTION 3 - the converter chain was rebuilt per line
    -------------------------------------------------------
    Seven closures were allocated for every source line. The chain is a
    fixed table of bound methods built once in __init__.
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

        # Converters that never open a cursor set, in dispatch order.
        # Order matters: OBTAIN CALC must be offered the line before
        # OBTAIN FIRST / NEXT, and every declarative form before any
        # executable form.
        self._plain_converters = (
            (self._convert_declarative_or_control, ARITY_UPPER_LINE),
            (self._convert_finish_or_commit, ARITY_WITH_DIVISION),
            (self._convert_bind_ready_connect_disconnect, ARITY_WITH_DIVISION),
            (self._convert_status_abort_perform, ARITY_WITH_DIVISION),
            (self._convert_on_db_rec_not_found, ARITY_LINE),
            (self._convert_obtain_calc, ARITY_WITH_SQL_ERROR),
            (self._convert_find_current, ARITY_WITH_DIVISION),
        )

        # Converters that may also open a cursor set.
        self._cursor_converters = (
            self._convert_obtain_first_next,
            self._convert_find_first,
        )

    #
    # Per-program lifecycle
    #
    def reset(self) -> None:
        """Clear per-program state.

        MUST be called once per program by CobolTransformer.transform(),
        before the first transform_line(). Without it a batch run carries
        one program's diagnostics and unmapped records into the next.
        """
        self.messages = []
        self.unmapped_records = set()

    #
    # Public entry point
    #
    def transform_line(
        self,
        line: str,
        current_division: str,
        sql_error_paragraph: str,
    ) -> tuple[list[str], str]:
        stripped_line = str(line or "").strip()

        if not stripped_line:
            return [line], NO_OPENED_SET

        upper = stripped_line.upper()

        plain = self._run_plain_converters(
            upper=upper,
            stripped_line=stripped_line,
            current_division=current_division,
            sql_error_paragraph=sql_error_paragraph,
        )

        if plain is not None:
            return plain, NO_OPENED_SET

        cursor_lines, opened_set = self._run_cursor_converters(
            upper=upper,
            stripped_line=stripped_line,
            current_division=current_division,
        )

        if cursor_lines is not None:
            return cursor_lines, opened_set

        store_lines = self._convert_store_modify_erase(
            upper,
            stripped_line,
            current_division,
            sql_error_paragraph,
        )

        if self._is_converted(store_lines):
            return store_lines, NO_OPENED_SET

        return self._replace_idms_condition_tokens(line), NO_OPENED_SET

    #
    # Dispatch
    #
    def _run_plain_converters(
        self,
        *,
        upper: str,
        stripped_line: str,
        current_division: str,
        sql_error_paragraph: str,
    ) -> list[str] | None:
        """First converter that returns a non-empty result wins."""
        for converter, arity in self._plain_converters:
            result = self._invoke(
                converter=converter,
                arity=arity,
                upper=upper,
                stripped_line=stripped_line,
                current_division=current_division,
                sql_error_paragraph=sql_error_paragraph,
            )

            if self._is_converted(result):
                return result

        return None

    def _run_cursor_converters(
        self,
        *,
        upper: str,
        stripped_line: str,
        current_division: str,
    ) -> tuple[list[str] | None, str]:
        """Converters that may also report the IDMS set they opened."""
        for converter in self._cursor_converters:
            result, opened_set = converter(
                upper,
                stripped_line,
                current_division,
            )

            if self._is_converted(result):
                return result, str(opened_set or NO_OPENED_SET)

        return None, NO_OPENED_SET

    @staticmethod
    def _invoke(
        *,
        converter,
        arity: int,
        upper: str,
        stripped_line: str,
        current_division: str,
        sql_error_paragraph: str,
    ):
        if arity == ARITY_LINE:
            return converter(stripped_line)

        if arity == ARITY_UPPER_LINE:
            return converter(upper, stripped_line)

        if arity == ARITY_WITH_DIVISION:
            return converter(upper, stripped_line, current_division)

        return converter(
            upper,
            stripped_line,
            current_division,
            sql_error_paragraph,
        )

    @staticmethod
    def _is_converted(result) -> bool:
        """True only for a real replacement.

        None means "this converter does not handle the line".
        An EMPTY list used to mean the same thing by accident, but the old
        dispatcher accepted it and the source statement vanished with no
        *DB2: comment. Empty is now treated as "not handled".
        """
        return result is not None and len(result) > 0


__all__ = ["IdmsStatementTransformer"]