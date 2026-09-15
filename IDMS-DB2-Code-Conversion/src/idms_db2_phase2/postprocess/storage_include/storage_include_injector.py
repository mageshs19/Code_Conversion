# LOCATION: src/idms_db2_phase2/postprocess/storage_include/storage_include_injector.py
# ACTION: REPLACE ENTIRE FILE

"""DCLGEN + copybook include injection and reference scanning.

CORRECTION 1 - duplicate DCLGEN include
---------------------------------------
_existing_exec_sql_includes scanned the RAW program text with a pattern
that expects the single-line form:

    EXEC SQL INCLUDE DZBFARTV END-EXEC.

Two things defeated it.

First, InfrastructureBlockBuilder emits the three-line block form, and
after fixed-format sequencing the SEQUENCE NUMBERS sit between the
tokens:

    001080     EXEC SQL                                       01080000
    001090       INCLUDE DZBFARTV                             01090000
    001100     END-EXEC.                                      01100000

The pattern's \\s+ cannot span '01080000' and '001090', so the match
failed and DZBFARTV was reported absent.

Second, even on clean text the pattern only ever recognised one of the
two shapes this codebase emits.

The injector therefore added DZBFARTV a second time. A duplicated DCLGEN
include duplicates every data-name in the group, which the compiler
rejects. CHK-08.02 reported exactly this.

Detection now runs over LOGICAL lines through IncludeRenderer, which
recognises both shapes.

CORRECTION 2 - injected includes sat in Area A
----------------------------------------------
Injected includes came from self.generator.dclgen_include*, which
rendered them with a single leading space:

     EXEC SQL INCLUDE DZ01RSTV END-EXEC.

CHK-06.07 requires at least 4 body spaces, i.e. column 12. Emission now
goes through IncludeRenderer too, so shape and indent are decided in one
place for every emitter in the project.

Copybook COPY statements are untouched: they are not EXEC SQL includes
and have their own placement rules.
"""

from __future__ import annotations

from idms_db2_phase2.generators.db2_infrastructure.include_renderer import (
    IncludeRenderer,
)
from patterns.update_storage_include_patterns import (
    DCL_HOST_REFERENCE_PATTERN,
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

    # =================================================================
    # Shared include renderer
    # =================================================================
    @property
    def includes(self) -> IncludeRenderer:
        """Renderer and scanner shared with every other include emitter.

        Built lazily because this class is a mixin: the host supplies
        self.line_utils and self.generator, and there is no constructor
        of our own to hook.
        """
        renderer = getattr(self, "_include_renderer", None)
        if renderer is None:
            renderer = IncludeRenderer(self.line_utils)
            self._include_renderer = renderer
        return renderer

    # =================================================================
    # Restart DCLGEN include
    # =================================================================
    def ensure_dclgen_include(self, cobol_text, context, diagnostics):
        role = context.restart_dclgen
        if not role:
            diagnostics.append(RESTART_DCLGEN_UNAVAILABLE)
            return cobol_text

        include_name = self.includes.normalize(role.include_name)
        if not include_name:
            diagnostics.append(RESTART_DCLGEN_UNAVAILABLE)
            return cobol_text

        lines = self.line_utils.lines(cobol_text)

        if include_name in self.includes.existing(lines):
            diagnostics.append(
                DCLGEN_INCLUDE_EXISTS_TEMPLATE.format(include=include_name)
            )
            return cobol_text

        insert_index = self.line_utils.data_division_insert_line_index(lines)
        if insert_index < 0:
            diagnostics.append(
                SKIP_DATA_DIVISION_DCLGEN_TEMPLATE.format(include=include_name)
            )
            return cobol_text

        block = self.includes.render(include_name)
        updated_lines = (
            lines[:insert_index] + block + [""] + lines[insert_index:]
        )
        diagnostics.append(
            DCLGEN_INCLUDE_INJECTED_TEMPLATE.format(include=include_name)
        )
        return self.line_utils.join(updated_lines)

    # =================================================================
    # Referenced DCLGEN includes
    # =================================================================
    def ensure_referenced_dclgen_includes(self, cobol_text, diagnostics):
        lines = self.line_utils.lines(cobol_text)
        referenced = self._referenced_dclgen_includes(cobol_text)

        # Shape-agnostic and sequence-number safe. An include already
        # emitted as a three-line block counts as present and is never
        # injected a second time.
        missing = [
            include_name
            for include_name in self.includes.missing(lines, referenced)
            if include_name not in EXCLUDED_INCLUDE_NAMES
        ]

        if not missing:
            return cobol_text

        insert_index = self.line_utils.data_division_insert_line_index(lines)
        if insert_index < 0:
            diagnostics.append(SKIP_DATA_DIVISION_REFERENCED)
            return cobol_text

        include_lines: list[str] = []
        for include_name in missing:
            include_lines.extend(self.includes.render(include_name))
            diagnostics.append(
                REFERENCED_DCLGEN_INJECTED_TEMPLATE.format(
                    base=UPDATE_RESTART_DIAGNOSTICS[
                        "referenced_dclgen_injected"
                    ],
                    include=include_name,
                )
            )

        if not include_lines:
            return cobol_text

        updated_lines = (
            lines[:insert_index] + include_lines + [""] + lines[insert_index:]
        )
        return self.line_utils.join(updated_lines)

    # =================================================================
    # Copybook COPY member
    # =================================================================
    def ensure_copybook_include(self, cobol_text, context, diagnostics):
        """A COPY member, not an EXEC SQL include.

        Left on its original path deliberately: COPY has different
        placement rules and is not part of the DB2 include family.
        """
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
                SKIP_DATA_DIVISION_COPYBOOK_TEMPLATE.format(
                    include=include_name
                )
            )
            return cobol_text

        block = self.generator.copybook_include(context).splitlines()
        updated_lines = (
            lines[:insert_index] + block + [""] + lines[insert_index:]
        )
        diagnostics.append(
            COPY_INJECTED_TEMPLATE.format(
                base=UPDATE_RESTART_DIAGNOSTICS["copy_injected"],
                include=include_name,
            )
        )
        return self.line_utils.join(updated_lines)

    # =================================================================
    # Scanning
    # =================================================================
    def _existing_exec_sql_includes(self, cobol_text) -> set[str]:
        """Every include already present, WHICHEVER shape carries it.

        Retained for callers outside this class. The work is delegated to
        IncludeRenderer, which reads LOGICAL lines and so is immune both
        to the block form and to interleaved sequence numbers.
        """
        return self.includes.existing(self.line_utils.lines(cobol_text))

    def _referenced_dclgen_includes(self, cobol_text) -> list[str]:
        """Include names implied by DCLGEN host group references.

        DCLDZBFARTV -> DZBFARTV. Order preserved, de-duplicated,
        infrastructure includes excluded.
        """
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