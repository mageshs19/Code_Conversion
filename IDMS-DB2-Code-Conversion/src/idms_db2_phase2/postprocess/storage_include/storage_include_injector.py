from __future__ import annotations

import re

from patterns.update_restart_patterns import (
    EXEC_SQL_INCLUDE_TOKEN_PATTERN_TEMPLATE,
)
from patterns.update_storage_include_patterns import (
    DCL_HOST_REFERENCE_PATTERN,
    EXEC_SQL_INCLUDE_PATTERN,
)
from rules.update_restart_rules import UPDATE_RESTART_DIAGNOSTICS
from rules.update_storage_include_rules import (
    COPY_EXISTS_BY_RECORD_TEMPLATE,
    COPY_EXISTS_TEMPLATE,
    COPY_INJECTED_TEMPLATE,
    DCL_GROUP_PREFIX,
    DCLGEN_INCLUDE_EXISTS_TEMPLATE,
    DCLGEN_INCLUDE_INJECTED_TEMPLATE,
    EXCLUDED_INCLUDE_NAMES,
    REFERENCED_DCLGEN_INJECTED_TEMPLATE,
    RESTART_DCLGEN_UNAVAILABLE,
    SKIP_DATA_DIVISION_COPYBOOK_TEMPLATE,
    SKIP_DATA_DIVISION_DCLGEN_TEMPLATE,
    SKIP_DATA_DIVISION_REFERENCED,
)


class StorageIncludeInjector:
    """DCLGEN + copybook include injection and reference scanning."""

    def ensure_dclgen_include(self, cobol_text, context, diagnostics):
        role = context.restart_dclgen
        if not role:
            diagnostics.append(RESTART_DCLGEN_UNAVAILABLE)
            return cobol_text

        include_name = role.include_name
        include_pattern = re.compile(
            EXEC_SQL_INCLUDE_TOKEN_PATTERN_TEMPLATE.format(
                include_name=re.escape(include_name)
            ),
            flags=re.IGNORECASE,
        )
        if include_pattern.search(self.line_utils.logical_text(cobol_text)):
            diagnostics.append(
                DCLGEN_INCLUDE_EXISTS_TEMPLATE.format(include=include_name)
            )
            return cobol_text

        lines = self.line_utils.lines(cobol_text)
        insert_index = self.line_utils.data_division_insert_line_index(lines)
        if insert_index < 0:
            diagnostics.append(
                SKIP_DATA_DIVISION_DCLGEN_TEMPLATE.format(include=include_name)
            )
            return cobol_text

        block = self.generator.dclgen_include(role).splitlines()
        updated_lines = lines[:insert_index] + block + [""] + lines[insert_index:]
        diagnostics.append(
            DCLGEN_INCLUDE_INJECTED_TEMPLATE.format(include=include_name)
        )
        return self.line_utils.join(updated_lines)

    def ensure_referenced_dclgen_includes(self, cobol_text, diagnostics):
        existing = self._existing_exec_sql_includes(cobol_text)
        referenced = self._referenced_dclgen_includes(cobol_text)
        missing = [inc for inc in referenced if inc not in existing]
        if not missing:
            return cobol_text

        lines = self.line_utils.lines(cobol_text)
        insert_index = self.line_utils.data_division_insert_line_index(lines)
        if insert_index < 0:
            diagnostics.append(SKIP_DATA_DIVISION_REFERENCED)
            return cobol_text

        include_lines: list[str] = []
        for include_name in missing:
            if include_name in EXCLUDED_INCLUDE_NAMES:
                continue
            include_lines.extend(
                self.generator.dclgen_include_by_name(include_name).splitlines()
            )
            diagnostics.append(
                REFERENCED_DCLGEN_INJECTED_TEMPLATE.format(
                    base=UPDATE_RESTART_DIAGNOSTICS["referenced_dclgen_injected"],
                    include=include_name,
                )
            )

        if not include_lines:
            return cobol_text

        updated_lines = (
            lines[:insert_index] + include_lines + [""] + lines[insert_index:]
        )
        return self.line_utils.join(updated_lines)

    def ensure_copybook_include(self, cobol_text, context, diagnostics):
        include_name = context.copybook_include_name
        record_name = context.input_record_name

        if self.line_utils.contains_copy(cobol_text, include_name):
            diagnostics.append(
                COPY_EXISTS_TEMPLATE.format(
                    base=UPDATE_RESTART_DIAGNOSTICS["copy_exists"],
                    include=include_name,
                )
            )
            return cobol_text

        if record_name != include_name and self.line_utils.contains_copy(
            cobol_text, record_name
        ):
            diagnostics.append(
                COPY_EXISTS_BY_RECORD_TEMPLATE.format(record=record_name)
            )
            return cobol_text

        lines = self.line_utils.lines(cobol_text)
        insert_index = self.line_utils.data_division_insert_line_index(lines)
        if insert_index < 0:
            diagnostics.append(
                SKIP_DATA_DIVISION_COPYBOOK_TEMPLATE.format(include=include_name)
            )
            return cobol_text

        block = self.generator.copybook_include(context).splitlines()
        updated_lines = lines[:insert_index] + block + [""] + lines[insert_index:]
        diagnostics.append(
            COPY_INJECTED_TEMPLATE.format(
                base=UPDATE_RESTART_DIAGNOSTICS["copy_injected"],
                include=include_name,
            )
        )
        return self.line_utils.join(updated_lines)

    def _existing_exec_sql_includes(self, cobol_text) -> set[str]:
        output: set[str] = set()
        for match in EXEC_SQL_INCLUDE_PATTERN.finditer(cobol_text):
            include_name = str(match.group("include") or "").strip().upper()
            if include_name:
                output.add(include_name)
        return output

    def _referenced_dclgen_includes(self, cobol_text) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()
        for match in DCL_HOST_REFERENCE_PATTERN.finditer(cobol_text):
            group_name = str(match.group("group") or "").strip().upper()
            if not group_name.startswith(DCL_GROUP_PREFIX):
                continue
            include_name = group_name[len(DCL_GROUP_PREFIX):]
            if not include_name or include_name in EXCLUDED_INCLUDE_NAMES:
                continue
            if include_name in seen:
                continue
            seen.add(include_name)
            output.append(include_name)
        return output