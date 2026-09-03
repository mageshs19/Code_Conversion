"""
Fixed-format COBOL body formatter.

Responsibilities:
- Decide Area A vs Area B.
- Preserve original indentation wherever possible.
- Keep original business COBOL indentation.
- Normalize generated SQL and generated procedure statements.

Regex patterns live in patterns/fixed_format_patterns.py; statement keyword
groups in rules/cobol_statement_rules.py; layout constants in
rules/fixed_format_rules.py.
"""

from __future__ import annotations

from patterns.fixed_format_patterns import (
    AREA_A_PREFIX_PATTERN,
    DATA_LEVEL_PATTERN,
    DIVISION_PATTERN,
    EXEC_SQL_END_PATTERN,
    EXEC_SQL_START_PATTERN,
    PARAGRAPH_PATTERN,
    SECTION_PATTERN,
)
from rules.cobol_statement_rules import (
    NON_PARAGRAPH_WORDS,
    PROCEDURE_VERBS,
    SQL_LEVEL_1_KEYWORDS,
    SQL_LEVEL_2_KEYWORDS,
)
from rules.fixed_format_rules import (
    AREA_A_DATA_LEVELS,
    AREA_B_INDENT,
    PRESERVE_VERBATIM_INDICATORS,
    PROCEDURE_DIVISION_NAME,
    SQL_INDENT,
)


class FixedFormatBodyFormatter:
    def area_body(
        self,
        body: str,
        logical: str,
        current_division: str,
        inside_exec_sql: bool,
        indicator: str,
        previous_procedure_indent: str,
    ) -> str:
        original = str(body or "").rstrip()
        clean_statement = str(logical or "").strip()

        if indicator in PRESERVE_VERBATIM_INDICATORS:
            return original

        if not clean_statement:
            return ""

        if original.startswith(" "):
            return original

        if self.is_area_a_statement(clean_statement):
            return clean_statement

        if inside_exec_sql:
            return self.sql_area_body(clean_statement)

        if current_division == PROCEDURE_DIVISION_NAME:
            return self.procedure_area_b_body(
                clean_statement=clean_statement,
                previous_procedure_indent=previous_procedure_indent,
            )

        if DATA_LEVEL_PATTERN.match(clean_statement):
            return self.data_area_body(clean_statement)

        return clean_statement

    def procedure_area_b_body(
        self,
        clean_statement: str,
        previous_procedure_indent: str,
    ) -> str:
        upper = clean_statement.upper()

        if self.is_area_a_statement(clean_statement):
            return clean_statement

        if upper.startswith(PROCEDURE_VERBS):
            return AREA_B_INDENT + clean_statement

        if previous_procedure_indent:
            return previous_procedure_indent + clean_statement

        return AREA_B_INDENT + clean_statement

    def data_area_body(self, clean_statement: str) -> str:
        parts = clean_statement.split(maxsplit=1)
        if not parts:
            return clean_statement

        level = parts[0]
        if level in AREA_A_DATA_LEVELS:
            return clean_statement

        return AREA_B_INDENT + clean_statement

    def sql_area_body(self, clean_statement: str) -> str:
        upper = clean_statement.upper()

        if EXEC_SQL_START_PATTERN.match(clean_statement):
            return AREA_B_INDENT + clean_statement

        if EXEC_SQL_END_PATTERN.match(clean_statement):
            return AREA_B_INDENT + clean_statement

        if upper.startswith(SQL_LEVEL_1_KEYWORDS):
            return SQL_INDENT + clean_statement

        if upper.startswith(SQL_LEVEL_2_KEYWORDS):
            return SQL_INDENT + clean_statement

        return SQL_INDENT + clean_statement

    def is_area_a_statement(self, statement: str) -> bool:
        clean_statement = str(statement or "").strip()
        if not clean_statement:
            return False

        if DIVISION_PATTERN.match(clean_statement):
            return True
        if SECTION_PATTERN.match(clean_statement):
            return True
        if AREA_A_PREFIX_PATTERN.match(clean_statement):
            return True

        if DATA_LEVEL_PATTERN.match(clean_statement):
            first_word = clean_statement.split(maxsplit=1)[0]
            return first_word in AREA_A_DATA_LEVELS

        if not PARAGRAPH_PATTERN.match(clean_statement):
            return False

        paragraph_name = clean_statement.rstrip(".").strip().upper()
        if paragraph_name in NON_PARAGRAPH_WORDS:
            return False

        return True

    def is_exec_sql_start(self, statement: str) -> bool:
        return bool(EXEC_SQL_START_PATTERN.match(str(statement or "").strip()))

    def is_exec_sql_end(self, statement: str) -> bool:
        return bool(EXEC_SQL_END_PATTERN.match(str(statement or "").strip()))

    def leading_spaces(self, text: str, default: str = "") -> str:
        value = str(text or "")
        if not value:
            return default

        count = len(value) - len(value.lstrip(" "))
        if count <= 0:
            return default

        return value[:count]