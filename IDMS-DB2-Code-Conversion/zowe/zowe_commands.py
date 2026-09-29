# LOCATION: zowe/zowe_commands.py
# ACTION: CREATE NEW FILE
"""Non-step commands: init, show, plan, clean."""

from __future__ import annotations

from zowe.zowe_console import bullets, credentials, header
from zowe.zowe_libraries import LibrarySearch
from zowe.zowe_programs import selected_programs
from zowe.zowe_resolver import resolve_dependencies
from zowe.zowe_rules import (
    ARTIFACT_COPYBOOK,
    ARTIFACT_DCLGEN,
    ARTIFACT_PROGRAM,
    ARTIFACT_SUBSCHEMA,
    CLEAN_REMOVED_TEMPLATE,
    EXIT_NOTHING,
    EXIT_OK,
    PIPELINE_TITLE,
    TEXT_ENCODING,
    WORKSPACE_CREATED_TEMPLATE,
    WORKSPACE_READY_TEMPLATE,
    ZOWE_RULES,
)
from zowe.zowe_settings import (
    application_code,
    build_output_profile,
    build_profiles,
)
from zowe.zowe_workspace import (
    clean_generated,
    count_files,
    ensure_workspace,
    mapping_dir,
    output_dir,
    program_dir,
    review_dir,
    workspace_root,
)

NOT_FOUND = "NOT FOUND"
COBOL_GLOB = "*.cbl"


def command_init() -> int:
    header(f"{PIPELINE_TITLE} - init")
    for folder in ensure_workspace():
        print(WORKSPACE_CREATED_TEMPLATE.format(folder=folder))
    print(WORKSPACE_READY_TEMPLATE.format(folder=workspace_root()))
    return EXIT_OK


def command_show() -> int:
    header(f"{PIPELINE_TITLE} - workspace")
    print(f"Workspace root : {workspace_root()}")
    print(f"Application    : {application_code()}")
    print(f"Mapping Sheet  : {count_files(mapping_dir())} file(s)")
    print(f"Programs       : {count_files(program_dir())} file(s)")
    print(f"Output         : {count_files(output_dir(), COBOL_GLOB)} file(s)")
    print(f"Reviews        : {count_files(review_dir())} file(s)")

    header(f"{PIPELINE_TITLE} - profile")
    for profile in build_profiles():
        print(f"{profile.label}")
        credentials(profile.key, profile.connection)
        print(f"  Libraries    : {', '.join(profile.libraries) or '(not set)'}")
        print(f"  Landing      : {profile.landing_dir}")
        print(f"  Mandatory    : {profile.mandatory}")
        print("")

    output = build_output_profile()
    print(f"{output.label}")
    credentials(output.key, output.connection)
    print(f"  Dataset      : {output.dataset or '(not set)'}")
    print(f"  Read only    : {output.read_only}")

    header("Rules")
    bullets(ZOWE_RULES)
    return EXIT_OK


def command_clean() -> int:
    header(f"{PIPELINE_TITLE} - clean")
    for folder in clean_generated():
        print(CLEAN_REMOVED_TEMPLATE.format(folder=folder))
    return EXIT_OK


def _report_one(label: str, member: str, search: LibrarySearch) -> int:
    """Print one resolution line. Returns 1 when unresolved."""
    where = search.locate(member) or NOT_FOUND
    print(f"  {label:<10}{member:<10} -> {where}")
    return 1 if where == NOT_FOUND else 0


def command_plan() -> int:
    """Resolve every dependency WITHOUT downloading them.

    Programs ARE downloaded: their text is the only way to learn what
    they need. No dependency file is written.
    """
    ensure_workspace()
    header(f"{PIPELINE_TITLE} - plan")
    print(f"Application : {application_code()}")

    programs = selected_programs()
    print(f"Programs    : {', '.join(programs)}")

    program_search = LibrarySearch(artifact=ARTIFACT_PROGRAM)
    copybook_search = LibrarySearch(artifact=ARTIFACT_COPYBOOK)
    dclgen_search = LibrarySearch(artifact=ARTIFACT_DCLGEN)
    subschema_search = LibrarySearch(artifact=ARTIFACT_SUBSCHEMA)

    missing = 0
    for program in programs:
        header(f"Program {program}")
        dataset, content = program_search.download(program)
        if not dataset:
            print(f"  {NOT_FOUND} in {', '.join(program_search.libraries)}")
            missing += 1
            continue
        print(f"  found in {dataset}")

        deps = resolve_dependencies(
            program, content.decode(TEXT_ENCODING, errors="replace")
        )

        for member in deps.copybooks:
            missing += _report_one("Copybook  ", member, copybook_search)

        for record, member in zip(deps.records, deps.dclgens):
            if not member:
                continue
            missing += _report_one("DCLGEN    ", member, dclgen_search)
            print(f"             (from IDMS record {record})")

        if deps.subschema:
            missing += _report_one("Subschema ", deps.subschema, subschema_search)
        else:
            print("  Subschema (none declared)")

    header("Plan summary")
    print(f"Unresolved members: {missing}")
    return EXIT_OK if missing == 0 else EXIT_NOTHING