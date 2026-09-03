from __future__ import annotations

from patterns.cobol_transformer_patterns import (
    BIND_STATEMENT_PATTERN,
    FIND_CURRENT_STATEMENT_PATTERN,
    FINISH_STATEMENT_PATTERN,
    IDMS_ABORT_PARAGRAPH_PATTERN,
    IDMS_DECLARATIVE_PATTERNS,
    IDMS_EXECUTABLE_PATTERNS,
    EXIT_LINE_PATTERN,
)


class IdmsResidualCleanup:
    """
    Detects and removes residual IDMS declarative/control/executable lines.

    This cleanup is conservative and preserves business flow by adding
    CONTINUE. when a removed executable statement appears in PROCEDURE DIVISION.
    """

    def is_idms_declarative_or_control(
        self,
        logical_line: str,
    ) -> bool:
        statement = str(logical_line or "").strip().rstrip(".")

        for pattern in IDMS_DECLARATIVE_PATTERNS:
            if pattern.search(statement):
                return True

        return False

    def is_idms_executable_cleanup(
        self,
        logical_line: str,
    ) -> bool:
        statement = str(logical_line or "").strip().rstrip(".")

        for pattern in IDMS_EXECUTABLE_PATTERNS:
            if pattern.search(statement):
                return True

        return False

    def is_idms_abort_paragraph(
        self,
        logical_line: str,
    ) -> bool:
        statement = str(logical_line or "").strip()

        return bool(IDMS_ABORT_PARAGRAPH_PATTERN.match(statement))

    def is_exit_line(
        self,
        logical_line: str,
    ) -> bool:
        statement = str(logical_line or "").strip()

        return bool(EXIT_LINE_PATTERN.match(statement))

    def removed_declarative_lines(
        self,
        logical_line: str,
    ) -> list[str]:
        return [
            f"* DB2: Removed residual IDMS control statement: {logical_line}",
        ]

    def removed_executable_lines(
        self,
        *,
        logical_line: str,
        current_division: str,
    ) -> list[str]:
        statement = str(logical_line or "").strip()

        if FINISH_STATEMENT_PATTERN.search(statement):
            if current_division == "PROCEDURE":
                return [
                    "* DB2: IDMS FINISH converted to COMMIT.",
                    "MOVE 'COMMIT' TO SQL-LOCATION.",
                    "EXEC SQL",
                    "    COMMIT",
                    "END-EXEC.",
                ]

            return [
                f"* DB2: Removed IDMS FINISH outside PROCEDURE DIVISION: {statement}",
            ]

        if BIND_STATEMENT_PATTERN.search(statement):
            return self.procedure_safe_removal(
                message=f"* DB2: Removed IDMS BIND statement: {statement}",
                current_division=current_division,
            )

        if FIND_CURRENT_STATEMENT_PATTERN.search(statement):
            return self.procedure_safe_removal(
                message=f"* DB2: Removed IDMS FIND CURRENT statement: {statement}",
                current_division=current_division,
            )

        return self.procedure_safe_removal(
            message=f"* DB2: Removed residual IDMS executable statement: {statement}",
            current_division=current_division,
        )

    def procedure_safe_removal(
        self,
        *,
        message: str,
        current_division: str,
    ) -> list[str]:
        if current_division == "PROCEDURE":
            return [
                message,
                "CONTINUE.",
            ]

        return [
            message,
        ]