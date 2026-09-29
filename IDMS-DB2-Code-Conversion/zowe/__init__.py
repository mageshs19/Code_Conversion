# LOCATION: zowe/__init__.py
# ACTION: REPLACE ENTIRE FILE
"""Zowe input source for the IDMS to DB2 conversion pipeline.

Self-contained: rules, patterns, settings, client, fetcher and writer all
live inside this package. The conversion pipeline is never imported here.
"""

from __future__ import annotations

from zowe.zowe_fetcher import ZoweFetcher, fetch_zowe_inputs
from zowe.zowe_libraries import LibrarySearch, application_code, libraries_for
from zowe.zowe_programs import selected_programs
from zowe.zowe_resolver import (
    ProgramDependencies,
    dclgen_member_for,
    resolve_dependencies,
)
from zowe.zowe_settings import (
    ArtifactProfile,
    ZoweConnection,
    artifact_connection,
    build_output_profile,
    build_profiles,
)
from zowe.zowe_workspace import ensure_workspace, workspace_root
from zowe.zowe_writer import upload_converted_folder, upload_converted_program

__all__ = [
    "ZoweFetcher",
    "fetch_zowe_inputs",
    "LibrarySearch",
    "application_code",
    "libraries_for",
    "selected_programs",
    "ProgramDependencies",
    "resolve_dependencies",
    "dclgen_member_for",
    "ArtifactProfile",
    "ZoweConnection",
    "artifact_connection",
    "build_profiles",
    "build_output_profile",
    "ensure_workspace",
    "workspace_root",
    "upload_converted_program",
    "upload_converted_folder",
]