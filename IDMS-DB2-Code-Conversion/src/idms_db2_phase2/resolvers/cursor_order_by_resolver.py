# LOCATION: src/idms_db2_phase2/resolvers/cursor_order_by_resolver.py
# ACTION: REPLACE ENTIRE FILE
"""Resolves cursor ORDER BY columns.

Parent cursors receive ORDER BY only when the Sheet Mapping explicitly
indicates order semantics. Child cursors use relationship-derived order
columns.

CORRECTION 1 - the two candidate paths validated differently
-------------------------------------------------------------
A Sheet Mapping row whose DB2 column cell reads FILLER reached the SQL:

    ORDER BY CT_RKTGDSV_479BFAS
           , ...
           , FILLER
           , NR_ID_479BFAS DESC

FILLER is a COBOL placeholder, not a DB2 column: SQLCODE -206 at bind
and the program never runs. Both paths now pass through ONE gate,
_valid_order_columns().

CORRECTION 2 - a sort direction was inferred from prose
--------------------------------------------------------
Substring matching made "DESC" match inside "DESCRIPTION", and the
dedicated hint list contains the very Hopex type remark carried by the
identity key - so the column the manual reference sorts ASC was emitted
DESC, reversing the extract file. Direction inference is OFF by default
and, when enabled, reads only DESC_HINT_FIELDS and matches whole WORDS.

CORRECTION 3 - the composite CALC key was ordered in full
-----------------------------------------------------------
The manual reference orders its ROOT cursor on the single identity key
ascending. A surrogate identity key is unique on its own, so the
remaining composite columns add sort cost without adding determinism.
_narrowed_order_columns() is now WIRED IN - previously it was defined
and never called, so the narrowing never happened. A record with NO
identity key keeps its full composite key: a resolved clause is refused,
never deleted.

CORRECTION 4 - diagnostics could abort the resolver
----------------------------------------------------
_log() formatted with **values. The message catalogues carry different
placeholders per producer, so one missing key raised KeyError inside the
code whose only job was to report. Formatting is now non-fatal and
template-tolerant.

No program, record, table, cursor or host variable name is hardcoded.
"""

from __future__ import annotations

from string import Formatter

from idms_db2_phase2.repositories.mapping_repository import MappingRepository
from idms_db2_phase2.resolvers.cursor_column_filter import CursorColumnFilter
from idms_db2_phase2.resolvers.relationship_resolver import RelationshipResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.cursor_column_rules import (
    CURSOR_ORDER_BY_MESSAGES,
    DESC_HINT_FIELDS,
    DESC_HINT_WORDS,
    EMIT_EXPLICIT_ASC,
    EMIT_ORDER_BY_DIRECTION,
    ENFORCE_ORDER_BY_COLUMN_VALIDATION,
    NON_COLUMN_SENTINELS,
    ORDER_BY_DIRECTION_ASC,
    ORDER_BY_DIRECTION_DESC,
    ORDER_HINT_WORDS,
)
from rules.cursor_declaration_rules import (
    ORDER_BY_KEY_MESSAGES,
    ORDER_BY_NARROWING_APPLIES_TO_CHILD,
    ORDER_BY_PREFER_IDENTITY_KEY,
    ORDER_BY_SOURCE_CHILD_KEY,
    ORDER_BY_SOURCE_PARENT_INTENT,
)
from rules.key_naming_rules import IDENTITY_KEY_PREFIXES

WORD_SEPARATORS = " \t,;:/()-_."

#: Every placeholder any ORDER BY template may ask for. A template that
#: wants {source} must never crash a caller that does not own one.
MESSAGE_PLACEHOLDER_DEFAULTS = {
    "record": "",
    "column": "",
    "columns": "",
    "count": 0,
    "total": 0,
    "kept": 0,
    "direction": "",
    "source": "",
}


def _prefix_tuple(prefixes) -> tuple[str, ...]:
    """Normalised upper-case tuple - str.startswith() requires a tuple."""
    return tuple(
        str(prefix or "").strip().upper()
        for prefix in (prefixes or ())
        if str(prefix or "").strip()
    )


class CursorOrderByResolver:
    """Resolves cursor ORDER BY columns."""

    #: ONE merged catalogue. A shared key is never shadowed and a missing
    #: key degrades to silence, not to an exception.
    MESSAGES = {
        **dict(ORDER_BY_KEY_MESSAGES or {}),
        **dict(CURSOR_ORDER_BY_MESSAGES or {}),
    }

    def __init__(
        self,
        mapping_repository: MappingRepository,
        relationship_resolver: RelationshipResolver,
        column_filter: CursorColumnFilter,
    ) -> None:
        self.mapping_repository = mapping_repository
        self.relationship_resolver = relationship_resolver
        self.column_filter = column_filter
        self.identity_prefixes = _prefix_tuple(IDENTITY_KEY_PREFIXES)
        self.messages: list[str] = []

    # -----------------------------------------------------------------
    # Per-program lifecycle
    # -----------------------------------------------------------------
    def reset(self) -> None:
        """Clear per-program diagnostics."""
        self.messages = []

    # -----------------------------------------------------------------
    # Public entry point
    # -----------------------------------------------------------------
    def order_by_columns_for_record(self, record_name: str) -> list[str]:
        record = NameNormalizer.normalize(record_name)
        if not record:
            return []

        is_child = self.relationship_resolver.has_foreign_keys(record)

        if is_child:
            candidates = self.order_by_base_columns_for_record(record)
            source = ORDER_BY_SOURCE_CHILD_KEY
        else:
            candidates = self.explicit_parent_order_columns(record)
            source = ORDER_BY_SOURCE_PARENT_INTENT

        # STEP 1 - one validation gate for both paths.
        columns = self._valid_order_columns(
            record_name=record,
            columns=candidates,
        )

        if not columns:
            self._log("none", record=record)
            return []

        # STEP 2 - minimal deterministic key. This call is the fix:
        #          the method previously existed but was never invoked.
        columns = self._narrowed_order_columns(
            record_name=record,
            columns=columns,
            is_child=is_child,
        )

        # STEP 3 - direction last, so narrowing never reads a suffixed name.
        expressions = [
            self._expression(record_name=record, column=column)
            for column in columns
        ]

        expressions = self.column_filter.unique(expressions)

        self._log(
            "resolved",
            record=record,
            count=len(expressions),
            columns=", ".join(expressions),
            source=source,
        )

        if not EMIT_ORDER_BY_DIRECTION:
            self._log(
                "direction_disabled",
                count=len(expressions),
                direction=ORDER_BY_DIRECTION_ASC,
            )

        return expressions

    # -----------------------------------------------------------------
    # Candidate sources
    # -----------------------------------------------------------------
    def explicit_parent_order_columns(self, record_name: str) -> list[str]:
        """Parent/root columns whose Sheet Mapping row states order intent.

        Validation is NOT done here: _valid_order_columns() is the single
        gate for both paths, so the two can never diverge again.
        """
        rows = self.mapping_repository.rows_for_record(record_name)
        output: list[str] = []

        for row in rows or []:
            text = " ".join(
                [
                    str(getattr(row, "remarks", "") or ""),
                    str(getattr(row, "hopex_expression_type_remark", "") or ""),
                    str(getattr(row, "relation", "") or ""),
                    str(getattr(row, "basetype", "") or ""),
                ]
            ).upper()

            if not self._mentions_any(text, ORDER_HINT_WORDS):
                continue

            column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
            )
            if column:
                output.append(column)

        return output

    def order_by_base_columns_for_record(self, record_name: str) -> list[str]:
        """Child columns derived from the record's own key."""
        return self.relationship_resolver.order_by_columns_for_record(
            record_name
        )

    # -----------------------------------------------------------------
    # The single validation gate
    # -----------------------------------------------------------------
    def _valid_order_columns(
        self,
        *,
        record_name: str,
        columns: list[str],
    ) -> list[str]:
        """Keep only real, non-audit DB2 columns of this record.

        Every rejection is reported: an ORDER BY that quietly shrinks is
        a change to the output file's row sequence.
        """
        if not ENFORCE_ORDER_BY_COLUMN_VALIDATION:
            return list(columns or [])

        kept: list[str] = []
        seen: set[str] = set()

        for raw in columns or []:
            column = NameNormalizer.normalize(raw)

            if not column or column.upper() in NON_COLUMN_SENTINELS:
                self._log(
                    "dropped_sentinel",
                    record=record_name,
                    column=str(raw or "").strip() or "(blank)",
                )
                continue

            if column in seen:
                continue

            if not self.column_filter.column_exists_for_record(
                record_name,
                column,
            ):
                self._log(
                    "dropped_not_a_column",
                    record=record_name,
                    column=column,
                )
                continue

            if self.column_filter.is_audit_column(column):
                self._log("dropped_audit", record=record_name, column=column)
                continue

            seen.add(column)
            kept.append(column)

        return kept

    # -----------------------------------------------------------------
    # Minimal deterministic key
    # -----------------------------------------------------------------
    def _narrowed_order_columns(
        self,
        *,
        record_name: str,
        columns: list[str],
        is_child: bool = False,
    ) -> list[str]:
        """The minimal key that is still deterministic.

        A surrogate identity key is unique on its own, so the remaining
        composite columns add sort cost without adding determinism. A
        record with NO identity key keeps its full composite key, so a
        resolved clause is never deleted - only ever refused.

        This is the same narrowing the UPDATE WHERE clause applies,
        reading the same prefix list from ONE module.
        """
        if not ORDER_BY_PREFER_IDENTITY_KEY or len(columns) <= 1:
            if columns:
                self._log(
                    "single_key",
                    record=record_name,
                    columns=", ".join(columns),
                )
            return columns

        if is_child and not ORDER_BY_NARROWING_APPLIES_TO_CHILD:
            self._log(
                "kept_composite_child",
                record=record_name,
                total=len(columns),
            )
            return columns

        identity = [
            column
            for column in columns
            if column.upper().startswith(self.identity_prefixes)
        ]

        if not identity:
            self._log(
                "kept_composite",
                record=record_name,
                total=len(columns),
            )
            return columns

        self._log(
            "narrowed_to_identity",
            record=record_name,
            total=len(columns),
            kept=len(identity),
            columns=", ".join(identity),
        )
        return identity

    # -----------------------------------------------------------------
    # Direction
    # -----------------------------------------------------------------
    def _expression(self, *, record_name: str, column: str) -> str:
        """'<column>', '<column> ASC' or '<column> DESC'."""
        if EMIT_ORDER_BY_DIRECTION and self.should_order_desc(
            record_name=record_name,
            column_name=column,
        ):
            return f"{column} {ORDER_BY_DIRECTION_DESC}"

        if EMIT_EXPLICIT_ASC:
            return f"{column} {ORDER_BY_DIRECTION_ASC}"

        return column

    def should_order_desc(self, record_name: str, column_name: str) -> bool:
        """True when a DEDICATED field states a descending sort.

        Only DESC_HINT_FIELDS are read, and matching is by whole WORD.
        Substring matching over prose reversed columns whose Remarks
        merely contained the word "description".
        """
        if not EMIT_ORDER_BY_DIRECTION:
            return False

        record = NameNormalizer.normalize(record_name)
        column = NameNormalizer.normalize(column_name)

        for row in self.mapping_repository.rows_for_record(record) or []:
            row_column = NameNormalizer.normalize(
                getattr(row, "new_db2_field_name", "")
            )
            if row_column != column:
                continue

            text = " ".join(
                str(getattr(row, field, "") or "")
                for field in DESC_HINT_FIELDS
            ).upper()

            if self._mentions_any(text, DESC_HINT_WORDS):
                return True

        return False

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    @staticmethod
    def _mentions_any(text: str, words) -> bool:
        """Whole-WORD membership test.

        'DESC' must not match inside 'DESCRIPTION'. Tokenising on the
        separators a spreadsheet cell actually uses is enough, and it
        keeps regex out of a resolver.
        """
        haystack = str(text or "").upper()
        for separator in WORD_SEPARATORS:
            haystack = haystack.replace(separator, " ")

        tokens = {token for token in haystack.split() if token}

        return any(str(word or "").strip().upper() in tokens for word in words)

    def _log(self, key: str, **values) -> None:
        """Diagnostics must never abort the resolver that emits them."""
        template = self.MESSAGES.get(key, "")
        if not template:
            return

        arguments = dict(MESSAGE_PLACEHOLDER_DEFAULTS)
        arguments.update(values)

        try:
            required = {
                field
                for _, field, _, _ in Formatter().parse(template)
                if field
            }
            missing = required - set(arguments)
            for name in missing:
                arguments[name] = ""

            message = template.format(**arguments)
        except (IndexError, ValueError, AttributeError):
            message = f"{template} [{key}: {values}]"

        message = message.strip()
        if message and message not in self.messages:
            self.messages.append(message)


__all__ = ["CursorOrderByResolver"]