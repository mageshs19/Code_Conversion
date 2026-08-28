# LOCATION: src/idms_db2_phase2/parsers/dclgen/sql_declare_parser.py
# ACTION: CREATE NEW FILE

"""Parses EXEC SQL DECLARE TABLE column definitions from DCLGEN text."""

from __future__ import annotations

from catalogs.db2_sql_types import DB2_SQL_SKIP_WORDS, DB2_SQL_TYPE_STARTERS
from patterns.dclgen_patterns import (
    DECLARE_TABLE_ALT_PATTERN,
    DECLARE_TABLE_PATTERN,
    DCLGEN_TABLE_COMMENT_PATTERN,
    VALID_SQL_COLUMN_NAME_PATTERN,
)


class SqlDeclareParser:
    def __init__(self, name_normalizer, diagnostics: list[str]) -> None:
        self.names = name_normalizer
        self.diagnostics = diagnostics

    def find_table_name(self, text: str) -> str:
        for pattern in [
            DECLARE_TABLE_PATTERN,
            DECLARE_TABLE_ALT_PATTERN,
            DCLGEN_TABLE_COMMENT_PATTERN,
        ]:
            match = pattern.search(text)
            if match:
                return self.names.normalize_sql_name(match.group(1))
        return ""

    def parse_columns(
        self,
        text: str,
        table_name: str,
        source_label: str,
    ) -> list[dict[str, object]]:
        sections = self._extract_declare_sections(text)

        if not sections:
            self.diagnostics.append(
                f"{source_label}: no EXEC SQL DECLARE TABLE section found."
            )
            return []

        output: list[dict[str, object]] = []

        for section_index, section in enumerate(sections, start=1):
            section_table = self.find_table_name(section) or table_name
            body = self._extract_parenthesized_body(section)

            if not body:
                self.diagnostics.append(
                    f"{source_label}: DECLARE section {section_index} has "
                    f"no column body."
                )
                continue

            parsed = self._parse_declare_body(
                body=body,
                table_name=section_table,
            )
            self.diagnostics.append(
                f"{source_label}: DECLARE section {section_index} parsed "
                f"SQL columns: {len(parsed)}"
            )
            output.extend(parsed)

        return output

    def _extract_declare_sections(self, text: str) -> list[str]:
        lines = text.splitlines()
        sections: list[str] = []
        current: list[str] = []
        inside = False

        for line in lines:
            upper = line.upper()

            if "DECLARE" in upper and "TABLE" in upper:
                inside = True
                current = [line]
                continue

            if inside:
                current.append(line)

                if "END-EXEC" in upper:
                    sections.append("\n".join(current))
                    current = []
                    inside = False
                    continue

                if upper.strip() == ")" or upper.strip().startswith(")"):
                    sections.append("\n".join(current))
                    current = []
                    inside = False
                    continue

        if inside and current:
            sections.append("\n".join(current))

        return sections

    def _extract_parenthesized_body(self, section: str) -> str:
        start = section.find("(")
        if start < 0:
            return ""

        depth = 0
        body_chars: list[str] = []

        for index in range(start, len(section)):
            char = section[index]

            if char == "(":
                depth += 1
                if depth == 1:
                    continue

            if char == ")":
                depth -= 1
                if depth == 0:
                    break

            if depth >= 1:
                body_chars.append(char)

        return "".join(body_chars)

    def _parse_declare_body(
        self,
        body: str,
        table_name: str,
    ) -> list[dict[str, object]]:
        logical_items = self._split_sql_items(body)

        inline_columns: list[dict[str, object]] = []
        column_names: list[str] = []
        db2_types: list[str] = []

        for item in logical_items:
            normalized_item = self._normalize_sql_item(item)
            if not normalized_item:
                continue

            inline = self._parse_inline_column_definition(
                normalized_item,
                table_name=table_name,
            )
            if inline:
                inline_columns.append(inline)
                continue

            if self._looks_like_column_name(normalized_item):
                column_names.append(
                    self.names.normalize_sql_name(normalized_item)
                )
                continue

            if self._looks_like_db2_type(normalized_item):
                db2_types.append(self._normalize_db2_type(normalized_item))
                continue

        if inline_columns:
            return inline_columns

        output: list[dict[str, object]] = []
        for index, column_name in enumerate(column_names):
            db2_type = db2_types[index] if index < len(db2_types) else ""
            output.append(
                {
                    "table_name": table_name,
                    "column_name": column_name,
                    "db2_type": db2_type,
                    "nullable": self._is_nullable_db2_type(db2_type),
                }
            )

        return output

    def _split_sql_items(self, body: str) -> list[str]:
        items: list[str] = []
        current: list[str] = []
        depth = 0
        normalized = body.replace("\n", " ")

        for char in normalized:
            if char == "(":
                depth += 1
                current.append(char)
                continue
            if char == ")":
                if depth > 0:
                    depth -= 1
                current.append(char)
                continue
            if char == "," and depth == 0:
                item = "".join(current).strip()
                if item:
                    items.append(item)
                current = []
                continue
            current.append(char)

        item = "".join(current).strip()
        if item:
            items.append(item)

        expanded: list[str] = []
        for item in items:
            expanded.extend(
                self._split_possible_stacked_column_or_type_lines(item)
            )

        return expanded

    def _split_possible_stacked_column_or_type_lines(
        self,
        item: str,
    ) -> list[str]:
        text = " ".join(str(item or "").split())
        if not text:
            return []

        inline = self._parse_inline_column_definition(text, table_name="")
        if inline:
            return [text]

        tokens = text.split()
        if len(tokens) <= 1:
            return [text]

        if self._looks_like_db2_type(text):
            return [text]

        if all(self._looks_like_column_name(token) for token in tokens):
            return tokens

        return [text]

    def _parse_inline_column_definition(
        self,
        item: str,
        table_name: str,
    ) -> dict[str, object] | None:
        tokens = item.split()
        if len(tokens) < 2:
            return None

        first = self.names.normalize_sql_name(tokens[0])
        if not self._looks_like_column_name(first):
            return None

        remaining = " ".join(tokens[1:])
        if not self._looks_like_db2_type(remaining):
            return None

        db2_type = self._normalize_db2_type(remaining)
        return {
            "table_name": table_name,
            "column_name": first,
            "db2_type": db2_type,
            "nullable": self._is_nullable_db2_type(db2_type),
        }

    def _looks_like_column_name(self, value: str) -> bool:
        text = self.names.normalize_sql_name(value)
        if not text:
            return False
        if text in DB2_SQL_SKIP_WORDS:
            return False
        if text.split(" ")[0] in DB2_SQL_TYPE_STARTERS:
            return False
        return bool(VALID_SQL_COLUMN_NAME_PATTERN.fullmatch(text))

    def _looks_like_db2_type(self, value: str) -> bool:
        text = str(value or "").strip().upper()
        if not text:
            return False
        first = text.split()[0]
        first = first.split("(", 1)[0]
        return first in DB2_SQL_TYPE_STARTERS

    def _normalize_sql_item(self, value: str) -> str:
        text = str(value or "").strip()
        text = text.strip(",").strip()
        text = " ".join(text.split())
        return text

    def _normalize_db2_type(self, value: str) -> str:
        text = " ".join(str(value or "").replace(", ", ",").split())
        text = text.rstrip(",")
        return text.upper()

    def _is_nullable_db2_type(self, db2_type: str) -> bool:
        return "NOT NULL" not in str(db2_type or "").upper()