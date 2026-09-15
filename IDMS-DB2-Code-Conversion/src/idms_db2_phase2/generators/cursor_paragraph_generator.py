# LOCATION: src/idms_db2_phase2/generators/cursor_paragraph_generator.py
# ACTION: REPLACE ENTIRE FILE

"""Generates DB2 cursor OPEN / FETCH / CLOSE paragraphs.

This class is a FACADE. It owns orchestration only:

- resolve the cursor specs (from Db2InfrastructureGenerator)
- normalise legacy SQL-ERROR references and rewrite PERFORM targets
  (CursorPerformRewriter)
- render each paragraph body (CursorParagraphBodyBuilder)
- insert the assembled block into the program once

Paragraph LAYOUT belongs to CursorParagraphBodyBuilder, not here. Banners,
debug trace lines, join-key diagnostics and counter increments are body
concerns and must be added there.

Public interface consumed by orchestration/conversion/conversion_pipeline.py:

    converted_cobol, messages = generator.apply(
        cobol_text=converted_cobol,
        operations=operations,
    )

Do not rename or remove `apply`.
"""

from __future__ import annotations

from catalogs.output_sections import DB2_CURSOR_PARAGRAPH_MARKER
from idms_db2_phase2.domain.models import IdmsOperation
from idms_db2_phase2.generators.cursor_paragraph.cursor_paragraph_body_builder import (
    CursorParagraphBodyBuilder,
)
from idms_db2_phase2.generators.cursor_paragraph.cursor_perform_rewriter import (
    CursorPerformRewriter,
)
from idms_db2_phase2.generators.db2_infrastructure_generator import (
    Db2InfrastructureGenerator,
)
from idms_db2_phase2.generators.sql_error_generator import SqlErrorGenerator
from idms_db2_phase2.resolvers.host_variable_resolver import HostVariableResolver
from patterns.db2_patterns import END_PROGRAM_PATTERN
from rules.cursor_paragraph_rules import (
    COMMENT_BLOCK_TEMPLATE,
    DIAG_BLOCK_EXISTS,
    DIAG_GENERATED_TEMPLATE,
    DIAG_NO_CURSOR_OPERATIONS,
    DIAG_NO_HOST_VARIABLES_TEMPLATE,
    SQL_ERROR_PARAGRAPH_NAME,
)


class CursorParagraphGenerator:
    """Builds and inserts the generated cursor paragraph block."""

    SQLERROR_PARAGRAPH_NAME = SQL_ERROR_PARAGRAPH_NAME

    def __init__(
        self,
        db2_infrastructure_generator: Db2InfrastructureGenerator,
        host_variable_resolver: HostVariableResolver,
        sql_error_generator: SqlErrorGenerator,
        body_builder: CursorParagraphBodyBuilder | None = None,
        perform_rewriter: CursorPerformRewriter | None = None,
    ) -> None:
        self.db2_infrastructure_generator = db2_infrastructure_generator
        self.host_variable_resolver = host_variable_resolver
        self.sql_error_generator = sql_error_generator
        self.body_builder = body_builder or CursorParagraphBodyBuilder()
        self.perform_rewriter = perform_rewriter or CursorPerformRewriter()
        self.messages: list[str] = []

    # =================================================================
    # Public entry point - DO NOT RENAME
    # =================================================================
    def apply(
        self,
        cobol_text: str,
        operations: list[IdmsOperation],
    ) -> tuple[str, list[str]]:
        self.messages = []
        text = str(cobol_text or "")

        if not text:
            return text, self.messages

        cursor_specs = self._cursor_specs(operations=operations)

        if not cursor_specs:
            self.messages.append(DIAG_NO_CURSOR_OPERATIONS)
            return text, self.messages

        sql_error_paragraph = self._sql_error_paragraph_name()

        updated_text = self.perform_rewriter.normalize_sql_error_references(
            text
        )
        updated_text = self.perform_rewriter.rewrite(
            text=updated_text,
            cursor_specs=cursor_specs,
        )

        if DB2_CURSOR_PARAGRAPH_MARKER in updated_text:
            self.messages.append(DIAG_BLOCK_EXISTS)
            return updated_text, self.messages

        block = self.paragraph_block(
            cursor_specs=cursor_specs,
            sql_error_paragraph=sql_error_paragraph,
        )
        updated_text = self._insert_paragraph_block(
            text=updated_text,
            block=block,
        )

        self.messages.append(
            DIAG_GENERATED_TEMPLATE.format(count=len(cursor_specs))
        )
        self.messages.extend(self._host_variable_warnings(cursor_specs))
        return updated_text, self.messages

    # =================================================================
    # Block assembly
    # =================================================================
    def paragraph_block(
        self,
        cursor_specs: list[dict[str, object]],
        sql_error_paragraph: str,
    ) -> str:
        lines: list[str] = []
        lines.extend(self._comment_block(DB2_CURSOR_PARAGRAPH_MARKER))
        lines.append("")

        for spec in cursor_specs:
            cursor_name = str(spec.get("cursor_name", ""))
            if not cursor_name:
                continue

            host_variables = list(spec.get("host_variables", []) or [])

            builders = (
                ("open_paragraph", self.open_paragraph, False),
                ("fetch_paragraph", self.fetch_paragraph, True),
                ("close_paragraph", self.close_paragraph, False),
            )

            for key, builder, needs_hosts in builders:
                paragraph_name = str(spec.get(key, ""))
                if not paragraph_name:
                    continue

                if needs_hosts:
                    lines.extend(
                        builder(
                            cursor_name=cursor_name,
                            paragraph_name=paragraph_name,
                            host_variables=host_variables,
                            sql_error_paragraph=sql_error_paragraph,
                        )
                    )
                else:
                    lines.extend(
                        builder(
                            cursor_name=cursor_name,
                            paragraph_name=paragraph_name,
                            sql_error_paragraph=sql_error_paragraph,
                        )
                    )

                lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    # =================================================================
    # Body delegation
    # =================================================================
    def open_paragraph(
        self,
        cursor_name: str,
        paragraph_name: str,
        sql_error_paragraph: str,
    ) -> list[str]:
        return self.body_builder.open_paragraph(
            cursor_name=cursor_name,
            paragraph_name=paragraph_name,
            sql_error_paragraph=sql_error_paragraph,
        )

    def fetch_paragraph(
        self,
        cursor_name: str,
        paragraph_name: str,
        host_variables: list[str],
        sql_error_paragraph: str,
    ) -> list[str]:
        return self.body_builder.fetch_paragraph(
            cursor_name=cursor_name,
            paragraph_name=paragraph_name,
            host_variables=self._clean_host_variables(host_variables),
            sql_error_paragraph=sql_error_paragraph,
        )

    def close_paragraph(
        self,
        cursor_name: str,
        paragraph_name: str,
        sql_error_paragraph: str,
    ) -> list[str]:
        return self.body_builder.close_paragraph(
            cursor_name=cursor_name,
            paragraph_name=paragraph_name,
            sql_error_paragraph=sql_error_paragraph,
        )

    # =================================================================
    # Helpers
    # =================================================================
    def _sql_error_paragraph_name(self) -> str:
        """Single source of truth for the SQL error paragraph name."""
        name = str(
            getattr(self.sql_error_generator, "PARAGRAPH_NAME", "") or ""
        ).strip()
        return name or self.SQLERROR_PARAGRAPH_NAME

    def _cursor_specs(
        self,
        operations: list[IdmsOperation],
    ) -> list[dict[str, object]]:
        """Reuse the specs the infrastructure generator already built."""
        cached_specs = getattr(
            self.db2_infrastructure_generator,
            "last_cursor_specs",
            [],
        )
        if cached_specs:
            return cached_specs

        return self.db2_infrastructure_generator.cursor_specs(operations)

    @staticmethod
    def _clean_host_variables(host_variables: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()

        for host in host_variables or []:
            value = str(host or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            out.append(value)

        return out

    @staticmethod
    def _comment_block(title: str) -> list[str]:
        return [COMMENT_BLOCK_TEMPLATE.format(title=title)]

    def _host_variable_warnings(
        self,
        cursor_specs: list[dict[str, object]],
    ) -> list[str]:
        warnings: list[str] = []

        for spec in cursor_specs:
            if list(spec.get("host_variables", []) or []):
                continue
            warnings.append(
                DIAG_NO_HOST_VARIABLES_TEMPLATE.format(
                    cursor=str(spec.get("cursor_name", "")),
                    record=str(spec.get("record_name", "")),
                    table=str(spec.get("table_name", "")),
                )
            )

        return warnings

    @staticmethod
    def _insert_paragraph_block(text: str, block: str) -> str:
        """Place the block before END PROGRAM, else append at the end."""
        match = END_PROGRAM_PATTERN.search(text)

        if match:
            insert_at = match.start()
            return f"{text[:insert_at]}\n{block}\n{text[insert_at:]}"

        return f"{text.rstrip()}\n\n{block}"