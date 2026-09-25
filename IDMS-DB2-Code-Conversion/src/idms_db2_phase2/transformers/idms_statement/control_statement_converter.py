# LOCATION: src/idms_db2_phase2/transformers/idms_statement/control_statement_converter.py
# ACTION: REPLACE ENTIRE FILE
"""IDMS declarative and control statement conversion.

Conversion logic only. Regex patterns live in patterns/idms_patterns.py;
all *DB2: message text lives in rules/idms_transformer_messages.py.

THIS IS A MIXIN
---------------
IdmsStatementTransformer composes it:

    class IdmsStatementTransformer(
        TransformerSharedMixin,
        ControlStatementConverterMixin,
        DataStatementConverterMixin,
    ):

The host owns construction and owns `messages`, which reset() clears once
per program. This module declares NO __init__ and NEVER rebinds
`self.messages`.

DISPATCHER CONTRACT - FOUR REGISTERED CONVERTERS
------------------------------------------------
IdmsStatementTransformer.__init__ builds a fixed table of bound methods.
Every name and arity below is a contract. Renaming one raises
AttributeError at construction; changing its parameter count raises
TypeError on the first line converted.

    (self._convert_declarative_or_control,        ARITY_UPPER_LINE)
    (self._convert_finish_or_commit,              ARITY_WITH_DIVISION)
    (self._convert_bind_ready_connect_disconnect, ARITY_WITH_DIVISION)
    (self._convert_status_abort_perform,          ARITY_WITH_DIVISION)

    ARITY_UPPER_LINE    -> (upper, stripped_line)
    ARITY_WITH_DIVISION -> (upper, stripped_line, current_division)

Declaratives are arity 2 because they are non-executable: their removal
never needs CONTINUE, so the division is irrelevant. The three executable
families are arity 3 because a removal inside PROCEDURE DIVISION must
carry CONTINUE.

RETURN CONTRACT - ONLY A NON-EMPTY RESULT COUNTS
-------------------------------------------------
Per CORRECTION 2 in the host: the dispatcher treats only a NON-EMPTY list
as a conversion. None or [] falls through to the next converter, and
finally to token replacement, so a statement can never disappear without
a *DB2: comment explaining it.

PATTERN NAMING
--------------
FIND CURRENT is FIND_CURRENT_PATTERN in patterns/idms_patterns.py.
FIND_CURRENT_STATEMENT_PATTERN is a DIFFERENT name in
patterns/cobol_transformer_patterns.py, used by idms_residual_cleanup.py.

CORRECTION - COMMIT emitted in a read-only program
--------------------------------------------------
IDMS FINISH closes the run unit, so the DB2 equivalent in an UPDATE
program is COMMIT. A RETRIEVAL program declares every cursor
FOR READ ONLY and has nothing to commit; the manual reference emits none,
and rules/manual_reference_rules.py already declared
EMIT_COMMIT_IN_RETRIEVAL = False. Nothing read it.

ConversionComponentFactory publishes the policy onto the transformer
instance as `emit_commit`, classified ONCE from the SOURCE program, read
here with getattr(self, "emit_commit", True). The default True means any
caller that never sets a policy keeps the previous behaviour byte for
byte.
"""

from __future__ import annotations

from patterns.idms_patterns import (
    BIND_STATEMENT_PATTERN,
    COMMIT_PATTERN,
    CONNECT_STATEMENT_PATTERN,
    DISCONNECT_STATEMENT_PATTERN,
    FIND_CURRENT_PATTERN,
    FINISH_PATTERN,
    IDMS_ABORT_PERFORM_PATTERN,
    IDMS_STATUS_PERFORM_PATTERN,
    READY_PATTERN,
    USAGE_MODE_PATTERN,
)
from rules.idms_transformer_messages import (
    COMMIT_OUTSIDE_PROCEDURE_TEMPLATE,
    FINISH_CONVERTED_TO_COMMIT,
    FINISH_OUTSIDE_PROCEDURE_TEMPLATE,
    FINISH_REMOVED_RETRIEVAL,
    TRANSFORMER_MESSAGES,
)
from rules.manual_reference_rules import EMIT_COMMIT_IN_RETRIEVAL

PROCEDURE_DIVISION_NAME = "PROCEDURE"
CONTINUE_STATEMENT = "CONTINUE."

# Generated DB2 COMMIT block. One place, so the FINISH path and the
# explicit-COMMIT path can never drift apart.
COMMIT_BLOCK_LINES = (
    "MOVE 'COMMIT' TO SQL-LOCATION.",
    "EXEC SQL",
    "  COMMIT",
    "END-EXEC.",
)


class ControlStatementConverterMixin:
    """Converts IDMS declarative and control statements.

    Removal inside PROCEDURE DIVISION always carries CONTINUE, per
    CONVERSION_RULES: "When removing executable PROCEDURE DIVISION IDMS
    code, add CONTINUE."
    """

    # =================================================================
    # Converter 1 - declaratives.  Arity 2.
    # =================================================================
    def _convert_declarative_or_control(
        self,
        upper: str,
        stripped_line: str,
    ) -> list[str] | None:
        """Remove an IDMS declarative statement.

        Declaratives are non-executable - IDMS-CONTROL SECTION,
        PROTOCOL, SCHEMA SECTION, IDMS-RECORDS WITHIN, DB <rec> WITHIN,
        COPY IDMS, USAGE-MODE - so the removal is a comment only and no
        division is needed.

        Returns None when the line is not a declarative, so the
        dispatcher can offer it to the next converter.
        """
        statement = str(stripped_line or "").strip()
        if not statement:
            return None

        text = str(upper or statement)

        if USAGE_MODE_PATTERN.search(text):
            return [f"* DB2: Removed IDMS USAGE-MODE clause: {statement}"]

        if self._is_declarative(text):
            return [
                f"* DB2: Removed IDMS declarative statement: {statement}"
            ]

        return None

    # =================================================================
    # Converter 2 - FINISH and COMMIT.  Arity 3.
    # =================================================================
    def _convert_finish_or_commit(
        self,
        upper: str,
        stripped_line: str,
        current_division: str,
    ) -> list[str] | None:
        """Convert FINISH, and police an explicit COMMIT.

        Separated from the other control verbs because their OUTPUT
        depends on the division AND on whether the program is allowed to
        commit at all.
        """
        statement = str(stripped_line or "").strip()
        if not statement:
            return None

        division = self._division(current_division)

        if FINISH_PATTERN.search(statement):
            return self._finish_lines(
                statement=statement,
                current_division=division,
            )

        if COMMIT_PATTERN.search(statement):
            return self._commit_lines(
                statement=statement,
                current_division=division,
            )

        return None

    # =================================================================
    # Converter 3 - BIND / READY / CONNECT / DISCONNECT.  Arity 3.
    # =================================================================
    def _convert_bind_ready_connect_disconnect(
        self,
        upper: str,
        stripped_line: str,
        current_division: str,
    ) -> list[str] | None:
        """Remove run-unit and set-membership verbs.

        None of these has a DB2 equivalent: BIND and READY set up the
        IDMS run unit, CONNECT and DISCONNECT manage set membership, and
        FIND CURRENT establishes currency that a DB2 cursor position
        already provides.
        """
        statement = str(stripped_line or "").strip()
        if not statement:
            return None

        division = self._division(current_division)

        if BIND_STATEMENT_PATTERN.search(statement):
            return self._remove(
                f"* DB2: Removed IDMS BIND statement: {statement}",
                division,
            )

        if READY_PATTERN.search(statement):
            return self._remove(
                f"* DB2: Removed IDMS READY statement: {statement}",
                division,
            )

        if CONNECT_STATEMENT_PATTERN.search(statement):
            return self._remove(
                f"* DB2: Removed IDMS CONNECT statement: {statement}",
                division,
            )

        if DISCONNECT_STATEMENT_PATTERN.search(statement):
            return self._remove(
                f"* DB2: Removed IDMS DISCONNECT statement: {statement}",
                division,
            )

        if FIND_CURRENT_PATTERN.search(statement):
            return self._remove(
                f"* DB2: Removed IDMS FIND CURRENT statement: {statement}",
                division,
            )

        return None

    # =================================================================
    # Converter 4 - IDMS-STATUS / IDMS-ABORT PERFORM.  Arity 3.
    # =================================================================
    def _convert_status_abort_perform(
        self,
        upper: str,
        stripped_line: str,
        current_division: str,
    ) -> list[str] | None:
        """Remove PERFORM IDMS-STATUS and PERFORM IDMS-ABORT.

        Both are replaced by the generated EVALUATE SQLCODE blocks and
        the SQLERROR routine, so leaving either behind would call a
        paragraph the converted program no longer declares.
        """
        statement = str(stripped_line or "").strip()
        if not statement:
            return None

        text = str(upper or statement)
        division = self._division(current_division)

        if IDMS_STATUS_PERFORM_PATTERN.search(text):
            return self._remove(
                f"* DB2: Removed IDMS PERFORM IDMS-STATUS: {statement}",
                division,
            )

        if IDMS_ABORT_PERFORM_PATTERN.search(text):
            return self._remove(
                f"* DB2: Removed IDMS PERFORM IDMS-ABORT: {statement}",
                division,
            )

        return None

    # =================================================================
    # FINISH
    # =================================================================
    def _finish_lines(
        self,
        *,
        statement: str,
        current_division: str,
    ) -> list[str]:
        """FINISH -> COMMIT, but only when the program may commit.

        An UPDATE program commits. A RETRIEVAL program is read-only, so
        the statement is removed in the same shape every other removed
        IDMS verb uses, keeping the paragraph valid COBOL.
        """
        if current_division != PROCEDURE_DIVISION_NAME:
            return [
                FINISH_OUTSIDE_PROCEDURE_TEMPLATE.format(statement=statement)
            ]

        if not self._commit_allowed():
            self._log_control("commit_suppressed")
            return self._remove(FINISH_REMOVED_RETRIEVAL, current_division)

        self._log_control("commit_emitted")
        return [FINISH_CONVERTED_TO_COMMIT, *COMMIT_BLOCK_LINES]

    # =================================================================
    # COMMIT
    # =================================================================
    def _commit_lines(
        self,
        *,
        statement: str,
        current_division: str,
    ) -> list[str]:
        """An explicit COMMIT already present in the source.

        Subject to the SAME policy as FINISH. A COMMIT that survives
        into a read-only program is exactly the divergence this
        correction removes, whichever verb produced it.
        """
        if current_division != PROCEDURE_DIVISION_NAME:
            return [
                COMMIT_OUTSIDE_PROCEDURE_TEMPLATE.format(statement=statement)
            ]

        if not self._commit_allowed():
            self._log_control("commit_suppressed")
            return self._remove(FINISH_REMOVED_RETRIEVAL, current_division)

        self._log_control("commit_emitted")
        return list(COMMIT_BLOCK_LINES)

    # =================================================================
    # Policy
    # =================================================================
    def _commit_allowed(self) -> bool:
        """True only when this program may carry a COMMIT.

        An UPDATE program always may. A RETRIEVAL program may only if
        the site standard is flipped, which it is not by default.

        Read with getattr: this is a mixin and does not own the
        attribute. ConversionComponentFactory publishes it after the
        host is constructed.
        """
        if bool(getattr(self, "emit_commit", True)):
            return True
        return bool(EMIT_COMMIT_IN_RETRIEVAL)

    # =================================================================
    # Helpers
    # =================================================================
    @staticmethod
    def _division(current_division: str | None) -> str:
        return str(current_division or "").strip().upper()

    def _is_declarative(self, upper: str) -> bool:
        """Delegate to the host's declarative test when it exists.

        TransformerSharedMixin owns
        _is_idms_declarative_or_control_statement(), which scans
        IDMS_DECLARATIVE_OR_CONTROL_PATTERNS. Using it keeps one
        declarative definition in the codebase.
        """
        helper = getattr(self, "_is_idms_declarative_or_control_statement", None)
        if callable(helper):
            try:
                return bool(helper(upper))
            except Exception:  # noqa: BLE001
                return False
        return False

    def _remove(self, message: str, current_division: str) -> list[str]:
        """Route removal through the host helper when it exists.

        TransformerSharedMixin owns _removed_idms_executable_lines().
        Using it keeps one removal shape across every converter. The
        local fallback is identical, so behaviour is unchanged if the
        host helper is absent.
        """
        helper = getattr(self, "_removed_idms_executable_lines", None)
        if callable(helper):
            try:
                return list(helper(message, current_division))
            except Exception:  # noqa: BLE001
                pass

        return self.procedure_safe_removal(
            message=message,
            current_division=current_division,
        )

    def procedure_safe_removal(
        self,
        *,
        message: str,
        current_division: str,
    ) -> list[str]:
        """Comment the removed statement; keep the paragraph valid.

        An empty PROCEDURE DIVISION sentence does not compile, so a
        removal inside PROCEDURE always carries CONTINUE. Outside
        PROCEDURE the comment alone is enough.
        """
        if current_division == PROCEDURE_DIVISION_NAME:
            return [
                message,
                CONTINUE_STATEMENT,
            ]
        return [message]

    # =================================================================
    # Diagnostics
    # =================================================================
    def _log_control(self, key: str, **values) -> None:
        """Append to the HOST's message list; never create one.

        `messages` is owned by IdmsStatementTransformer and cleared by
        reset() once per program. Re-binding it here would reintroduce
        the cross-program leak that reset() exists to prevent.
        """
        template = TRANSFORMER_MESSAGES.get(key, "")
        if not template:
            return

        messages = getattr(self, "messages", None)
        if messages is None:
            return

        messages.append(template.format(**values))


__all__ = ["ControlStatementConverterMixin"]