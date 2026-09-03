from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any

from idms_db2_phase2.postprocess.update_cobol_file_resolver import (
    UpdateCobolFileResolver,
)
from idms_db2_phase2.postprocess.update_copybook_resolver import (
    UpdateCopybookResolver,
)
from idms_db2_phase2.postprocess.update_metadata_models import (
    CobolFileInfo,
    CopybookRecordInfo,
    DclgenRoleInfo,
    UpdateProgramContext,
)
from idms_db2_phase2.postprocess.update_restart_dclgen_resolver import (
    UpdateRestartDclgenResolver,
)
from idms_db2_phase2.services.name_derivation_resolver import (
    NameDerivationResolver,
)

class DynamicMetadataResolver:
    """
    Resolves update-program metadata from parsed COBOL, Copybook, and DCLGEN data.

    This resolver is used only by update postprocess.
    It does not hardcode program-specific copybook names, DCLGEN names,
    DB2 table names, or host variables.

    Restart role matching is delegated to UpdateRestartDclgenResolver and is
    token-driven through rules/update_restart_rules.py.
    """

    def __init__(self) -> None:
        self.cobol_resolver = UpdateCobolFileResolver()
        self.copybook_resolver = UpdateCopybookResolver()
        self.restart_dclgen_resolver = UpdateRestartDclgenResolver()
        self.name_derivation_resolver = NameDerivationResolver()  # ADDED

    def resolve(
        self,
        *,
        source_cobol: str,
        generated_cobol: str,
        copybook_fields: list[Any],
        dclgen_columns: list[Any],
        target_program_id: str = "",
        mapping_repository: Any | None = None,        # ADDED
    ) -> UpdateProgramContext:
        diagnostics: list[str] = []

        program_id = self.cobol_resolver.resolve_program_id(
            generated_cobol=generated_cobol,
            source_cobol=source_cobol,
            target_program_id=target_program_id,
        )
        diagnostics.append(f"Resolved PROGRAM-ID: {program_id}")

        input_files = self.cobol_resolver.parse_cobol_files(
            source_cobol=source_cobol,
            generated_cobol=generated_cobol,
        )

        if not input_files:
            raise ValueError("Unable to resolve input file from COBOL SELECT/FD/READ.")

        input_file = self.cobol_resolver.choose_input_file(input_files)
        diagnostics.append(f"Resolved input file: {input_file.name}")
        diagnostics.append(f"Resolved FD record: {input_file.fd_record}")
        diagnostics.append(f"Resolved record length: {input_file.record_length}")
        diagnostics.append(f"Resolved READ target: {input_file.read_target}")

        copybooks = self.copybook_resolver.build_copybook_records(copybook_fields)
        diagnostics.append(f"Resolved copybook record candidates: {len(copybooks)}")

        source_refs = self.cobol_resolver.extract_source_field_references(
            source_cobol
        )
        copy_statements = self.cobol_resolver.extract_copy_statements(
            source_cobol + "\n" + generated_cobol
        )

        input_copybook = self.copybook_resolver.choose_copybook(
            input_file=input_file,
            copybooks=copybooks,
            copy_statements=copy_statements,
            source_refs=source_refs,
        )
        # Apply the deterministic VM...BD... -> VMDZ... derivation to the
        # input record and copybook include names, matching the manual's
        # program-ID rule (e.g. VMBD205I -> VMDZ205I). Generic + rule-driven;
        # non-matching names are returned unchanged. If nothing changes, the
        # original copybook is kept as-is.
        derived_record = self.name_derivation_resolver.derive(
            input_copybook.record_name
        )
        derived_include = self.name_derivation_resolver.derive(
            input_copybook.include_name
        )

        if (
            derived_record != input_copybook.record_name
            or derived_include != input_copybook.include_name
        ):
            input_copybook = CopybookRecordInfo(
                include_name=derived_include,
                record_name=derived_record,
                source_label=input_copybook.source_label,
                fields=input_copybook.fields,
                estimated_length=input_copybook.estimated_length,
            )
            diagnostics.append(
                "Derived input record/copybook name via VM...BD...->VMDZ "
                f"rule: {derived_record} (COPY {derived_include})."
            )
        diagnostics.append(f"Resolved copybook include: {input_copybook.include_name}")
        diagnostics.append(f"Resolved copybook 01 record: {input_copybook.record_name}")
        diagnostics.append(
            f"Resolved copybook length: {input_copybook.estimated_length}"
        )

        legacy_eof_switch = self.cobol_resolver.resolve_legacy_eof_switch(
            source_cobol=source_cobol,
            generated_cobol=generated_cobol,
        )

        if legacy_eof_switch:
            diagnostics.append(f"Resolved legacy EOF switch: {legacy_eof_switch}")
        else:
            diagnostics.append("Legacy EOF switch not resolved.")

        restart_dclgen = self.restart_dclgen_resolver.resolve_restart_dclgen(
            dclgen_columns,
            mapping_repository=mapping_repository,     # ADDED
        )

        if restart_dclgen:
            diagnostics.append(f"Resolved restart table: {restart_dclgen.table_name}")
            diagnostics.append(
                f"Resolved restart include: {restart_dclgen.include_name}"
            )
            diagnostics.append(
                "Resolved restart host record: "
                f"{self._safe_attr(restart_dclgen, 'host_record_name')}"
            )
            diagnostics.append(
                "Resolved restart program column: "
                f"{self._safe_attr(restart_dclgen, 'program_column')}"
            )
            diagnostics.append(
                "Resolved restart program field: "
                f"{self._safe_attr(restart_dclgen, 'program_field')}"
            )
            diagnostics.append(
                "Resolved restart phase field: "
                f"{self._safe_attr(restart_dclgen, 'phase_field')}"
            )
            diagnostics.append(
                "Resolved restart date field: "
                f"{self._safe_attr(restart_dclgen, 'date_field')}"
            )
            diagnostics.append(
                "Resolved restart status field: "
                f"{self._safe_attr(restart_dclgen, 'status_field')}"
            )
            diagnostics.append(
                "Resolved restart retention field: "
                f"{self._safe_attr(restart_dclgen, 'retention_field')}"
            )
            diagnostics.append(
                "Resolved restart payload column: "
                f"{self._safe_attr(restart_dclgen, 'payload_column')}"
            )
            diagnostics.append(
                "Resolved restart payload group: "
                f"{self._safe_attr(restart_dclgen, 'payload_group')}"
            )
            diagnostics.append(
                "Resolved restart payload length field: "
                f"{self._safe_attr(restart_dclgen, 'payload_len_field')}"
            )
            diagnostics.append(
                "Resolved restart payload text field: "
                f"{self._safe_attr(restart_dclgen, 'payload_text_field')}"
            )
        else:
            # ADDED: distinguish Case 3 (mapping-confirmation failed) in logs
            if mapping_repository is not None and dclgen_columns:
                diagnostics.append(
                    "Restart flow skipped: a DCLGEN restart group was found "
                    "but the restart table is not present in the Sheet "
                    "Mapping. AND-gate not satisfied (Case 3)."
                )
            diagnostics.append("Restart DCLGEN not resolved.")

        return self._make_context(
            input_file=input_file,
            input_copybook=input_copybook,
            restart_dclgen=restart_dclgen,
            program_id=program_id,
            legacy_eof_switch=legacy_eof_switch,
            source_program_text=source_cobol,
            diagnostics=diagnostics,
        )

    def _make_context(
        self,
        **values: Any,
    ) -> UpdateProgramContext:
        """
        Creates UpdateProgramContext while staying compatible with the actual
        dataclass in update_metadata_models.py.

        The current uploaded model requires:
        - input_file
        - input_copybook
        - restart_dclgen
        - program_id

        Optional values are passed only if the local dataclass supports them.
        """

        if is_dataclass(UpdateProgramContext):
            accepted = {field.name for field in fields(UpdateProgramContext)}
            kwargs = {
                key: value
                for key, value in values.items()
                if key in accepted
            }
            context = UpdateProgramContext(**kwargs)
        else:
            context = UpdateProgramContext()

        for key, value in values.items():
            if not hasattr(context, key):
                try:
                    setattr(context, key, value)
                except Exception:
                    pass

        return context

    def _safe_attr(
        self,
        obj: Any,
        name: str,
    ) -> str:
        return str(getattr(obj, name, "") or "")


__all__ = [
    "CobolFileInfo",
    "CopybookRecordInfo",
    "DclgenRoleInfo",
    "DynamicMetadataResolver",
    "UpdateProgramContext",
]