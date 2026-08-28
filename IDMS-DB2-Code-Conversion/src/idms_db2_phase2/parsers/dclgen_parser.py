# LOCATION: src/idms_db2_phase2/parsers/dclgen_parser.py
# ACTION: REPLACE ENTIRE FILE

"""
Parses DB2 DCLGEN text files.

Thin facade delegating to focused helpers. Public API preserved:
- parse_many_texts(texts) -> list[DclgenColumn]
- parse(text, source_label) -> list[DclgenColumn]
- diagnostics attribute

Static content stays externalized:
- SQL type names: catalogs/db2_sql_types.py
- DCLGEN suffix rules: catalogs/dclgen_schema.py
- Regex patterns: patterns/dclgen_patterns.py
"""

from __future__ import annotations

from idms_db2_phase2.domain.models import DclgenColumn
from idms_db2_phase2.parsers.base_text_parser import BaseTextParser
from idms_db2_phase2.parsers.dclgen.cobol_host_field_parser import (
    CobolHostFieldParser,
)
from idms_db2_phase2.parsers.dclgen.dclgen_column_merger import (
    DclgenColumnMerger,
)
from idms_db2_phase2.parsers.dclgen.sql_declare_parser import SqlDeclareParser
from idms_db2_phase2.parsers.dclgen.sql_name_normalizer import (
    DclgenNameNormalizer,
)


class DclgenParser(BaseTextParser):
    def __init__(self) -> None:
        self.diagnostics: list[str] = []
        self._names = DclgenNameNormalizer()
        self._merger = DclgenColumnMerger(self._names)

    def parse_many_texts(
        self,
        texts: list[str],
    ) -> list[DclgenColumn]:
        self.diagnostics = []
        output: list[DclgenColumn] = []

        self.diagnostics.append(f"DCLGEN input file count: {len(texts)}")

        for index, text in enumerate(texts, start=1):
            source_label = f"DCLGEN file {index}"
            self.diagnostics.append(
                f"{source_label} input length: {len(text or '')}"
            )
            parsed = self.parse(text=text, source_label=source_label)
            self.diagnostics.append(
                f"{source_label} parsed columns: {len(parsed)}"
            )
            output.extend(parsed)

        self.diagnostics.append(
            f"DCLGEN total parsed columns: {len(output)}"
        )
        return output

    def parse(
        self,
        text: str,
        source_label: str = "DCLGEN",
    ) -> list[DclgenColumn]:
        if not text or not text.strip():
            self.diagnostics.append(f"{source_label}: empty text.")
            return []

        cleaned_text = self.clean_text(text)

        sql_declare_parser = SqlDeclareParser(
            name_normalizer=self._names,
            diagnostics=self.diagnostics,
        )
        cobol_field_parser = CobolHostFieldParser(
            diagnostics=self.diagnostics,
        )

        table_name = sql_declare_parser.find_table_name(cleaned_text)
        if table_name:
            self.diagnostics.append(
                f"{source_label}: resolved table name: {table_name}"
            )
        else:
            self.diagnostics.append(
                f"{source_label}: table name not found."
            )

        sql_columns = sql_declare_parser.parse_columns(
            text=cleaned_text,
            table_name=table_name,
            source_label=source_label,
        )
        cobol_fields = cobol_field_parser.parse(
            text=cleaned_text,
            source_label=source_label,
        )

        if sql_columns:
            output = self._merger.merge_sql_columns_with_cobol_hosts(
                sql_columns=sql_columns,
                cobol_fields=cobol_fields,
                fallback_table_name=table_name,
            )
            self.diagnostics.append(
                f"{source_label}: SQL columns parsed: {len(sql_columns)}"
            )
            self.diagnostics.append(
                f"{source_label}: COBOL host fields parsed: "
                f"{len(cobol_fields)}"
            )
            self.diagnostics.append(
                f"{source_label}: merged DCLGEN columns: {len(output)}"
            )
            return output

        if cobol_fields:
            self.diagnostics.append(
                f"{source_label}: no SQL DECLARE columns found; using "
                f"COBOL host fields as fallback."
            )
            return self._merger.fallback_columns_from_cobol_fields(
                table_name=table_name,
                cobol_fields=cobol_fields,
            )

        self.diagnostics.append(
            f"{source_label}: no SQL columns or COBOL host fields found."
        )
        return []