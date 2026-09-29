# LOCATION: zowe/zowe_fetcher.py
# ACTION: REPLACE ENTIRE FILE
"""Program-driven fetch.

For every program in the selected array:
    1. download the program from the first program library holding it
    2. read its COPY names           -> copybook libraries, in order
    3. derive DCLGEN members         -> DCLGEN libraries
    4. read its subschema name       -> subschema library (production)

Mapping Sheet is local and is never fetched.
"""

from __future__ import annotations

import logging
from pathlib import Path

from zowe.zowe_libraries import LibrarySearch, application_code, libraries_for
from zowe.zowe_resolver import ProgramDependencies, resolve_dependencies
from zowe.zowe_rules import (
    ARTIFACT_COPYBOOK,
    ARTIFACT_DCLGEN,
    ARTIFACT_EXTENSIONS,
    ARTIFACT_LABELS,
    ARTIFACT_PROGRAM,
    ARTIFACT_SUBSCHEMA,
    DIAG_APPLICATION_TEMPLATE,
    DIAG_DEPENDENCIES_TEMPLATE,
    DIAG_DERIVED_DCLGEN_TEMPLATE,
    DIAG_END_FETCH,
    DIAG_FOUND_TEMPLATE,
    DIAG_LIBRARY_ORDER_TEMPLATE,
    DIAG_MAPPING_LOCAL,
    DIAG_NOT_FOUND_TEMPLATE,
    DIAG_PROGRAM_LIST_TEMPLATE,
    DIAG_START_FETCH,
    DIAG_SUBSCHEMA_DETECTED_TEMPLATE,
    DIAG_TOTAL_TEMPLATE,
    TEXT_ENCODING,
    ZOWE_ERROR_MESSAGES,
    ZOWE_WARNING_MESSAGES,
)
from zowe.zowe_workspace import (
    copybook_dir,
    dclgen_dir,
    ensure_workspace,
    program_dir,
    subschema_dir,
)

logger = logging.getLogger("idms_db2_zowe")

_LANDING = {
    ARTIFACT_PROGRAM: program_dir,
    ARTIFACT_COPYBOOK: copybook_dir,
    ARTIFACT_DCLGEN: dclgen_dir,
    ARTIFACT_SUBSCHEMA: subschema_dir,
}


class ZoweFetcher:
    def __init__(self, programs: list[str] | None = None) -> None:
        from zowe.zowe_programs import selected_programs

        self.programs = programs or selected_programs()
        self.diagnostics: list[str] = []
        self.warnings: list[str] = []
        self.saved: dict[str, list[Path]] = {}
        self._searches: dict[str, LibrarySearch] = {}

    # ---- helpers ----
    def _search(self, artifact: str) -> LibrarySearch:
        if artifact not in self._searches:
            search = LibrarySearch(artifact=artifact)
            self._searches[artifact] = search
            self.diagnostics.append(
                DIAG_LIBRARY_ORDER_TEMPLATE.format(
                    label=search.label, libraries=", ".join(search.libraries)
                )
            )
        return self._searches[artifact]

    def _save(self, artifact: str, member: str, dataset: str, content: bytes) -> Path:
        folder = _LANDING[artifact]()
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{member}{ARTIFACT_EXTENSIONS[artifact]}"
        target.write_bytes(content)
        self.saved.setdefault(ARTIFACT_LABELS[artifact], []).append(target)
        self.diagnostics.append(
            DIAG_FOUND_TEMPLATE.format(
                label=ARTIFACT_LABELS[artifact],
                member=member,
                dataset=dataset,
                path=target,
            )
        )
        return target

    def _fetch_member(self, artifact: str, member: str, mandatory: bool) -> bool:
        search = self._search(artifact)
        dataset, content = search.download(member)

        if not dataset:
            libraries = ", ".join(search.libraries)
            self.diagnostics.append(
                DIAG_NOT_FOUND_TEMPLATE.format(
                    label=search.label, member=member, libraries=libraries
                )
            )
            message = (
                ZOWE_ERROR_MESSAGES["program_not_found"]
                if mandatory
                else ZOWE_WARNING_MESSAGES["member_not_found"]
            )
            formatted = message.format(
                label=search.label, member=member, libraries=libraries
            )
            if mandatory:
                raise ValueError(formatted)
            self.warnings.append(formatted)
            return False

        self._save(artifact, member, dataset, content)
        return True

    # ---- one program ----
    def _fetch_program(self, program: str) -> ProgramDependencies:
        search = self._search(ARTIFACT_PROGRAM)
        dataset, content = search.download(program)
        if not dataset:
            raise ValueError(
                ZOWE_ERROR_MESSAGES["program_not_found"].format(
                    member=program, libraries=", ".join(search.libraries)
                )
            )

        path = self._save(ARTIFACT_PROGRAM, program, dataset, content)
        source_text = path.read_text(encoding=TEXT_ENCODING, errors="replace")

        deps = resolve_dependencies(program, source_text)
        self.diagnostics.append(
            DIAG_DEPENDENCIES_TEMPLATE.format(
                program=program,
                copybooks=len(deps.copybooks),
                records=len(deps.records),
                subschema=deps.subschema or "(none)",
            )
        )
        return deps

    def _fetch_dependencies(self, deps: ProgramDependencies) -> None:
        for member in deps.copybooks:
            self._fetch_member(ARTIFACT_COPYBOOK, member, mandatory=False)

        for record, member in zip(deps.records, deps.dclgens):
            if not member:
                continue
            self.diagnostics.append(
                DIAG_DERIVED_DCLGEN_TEMPLATE.format(record=record, member=member)
            )
            self._fetch_member(ARTIFACT_DCLGEN, member, mandatory=False)

        if deps.subschema:
            self.diagnostics.append(
                DIAG_SUBSCHEMA_DETECTED_TEMPLATE.format(
                    program=deps.program, subschema=deps.subschema
                )
            )
            self._fetch_member(ARTIFACT_SUBSCHEMA, deps.subschema, mandatory=False)
        else:
            self.warnings.append(
                ZOWE_WARNING_MESSAGES["subschema_not_detected"].format(
                    program=deps.program
                )
            )

    # ---- all programs ----
    def fetch_all(self) -> dict:
        ensure_workspace()
        self.diagnostics.append(DIAG_START_FETCH)
        self.diagnostics.append(DIAG_MAPPING_LOCAL)
        self.diagnostics.append(
            DIAG_APPLICATION_TEMPLATE.format(application=application_code())
        )
        self.diagnostics.append(
            DIAG_PROGRAM_LIST_TEMPLATE.format(
                count=len(self.programs), names=", ".join(self.programs)
            )
        )

        for program in self.programs:
            deps = self._fetch_program(program)
            self._fetch_dependencies(deps)

        total = sum(len(v) for v in self.saved.values())
        self.diagnostics.append(
            DIAG_TOTAL_TEMPLATE.format(count=total, artifacts=len(self.saved))
        )
        self.diagnostics.append(DIAG_END_FETCH)

        return {
            "fetched": self.saved,
            "total_files": total,
            "diagnostics": self.diagnostics,
            "warnings": self.warnings,
        }


def fetch_zowe_inputs(source_text: str = "") -> dict:  # noqa: ARG001
    return ZoweFetcher().fetch_all()