# LOCATION: zowe/zowe_writer.py
# ACTION: CREATE NEW FILE
"""Write converted DB2 COBOL back to the configured output library."""

from __future__ import annotations

from pathlib import Path

from zowe.zowe_client import ZoweClient
from zowe.zowe_patterns import OUTPUT_STEM_PATTERN
from zowe.zowe_rules import (
    DIAG_UPLOAD_TEMPLATE,
    DIAG_VERIFIED_TEMPLATE,
    ZOWE_ERROR_MESSAGES,
)
from zowe.zowe_settings import ArtifactProfile, build_output_profile


def member_from_output_name(stem: str) -> str:
    """VMDZ7201_29-09-2026_143000 -> VMDZ7201"""
    match = OUTPUT_STEM_PATTERN.match(str(stem or ""))
    return ZoweClient.member_name(match.group("stem") if match else stem)


def upload_converted_program(
    source_file: Path,
    profile: ArtifactProfile | None = None,
    diagnostics: list[str] | None = None,
) -> tuple[str, str]:
    """Upload one generated file and verify it byte for byte."""
    profile = profile or build_output_profile()

    if not source_file.exists() or not source_file.is_file():
        raise FileNotFoundError(f"Source file does not exist: {source_file}")
    if not profile.dataset:
        raise ValueError(ZOWE_ERROR_MESSAGES["output_not_configured"])
    if profile.read_only:
        raise PermissionError(
            ZOWE_ERROR_MESSAGES["read_only"].format(dataset=profile.dataset)
        )

    client = ZoweClient(profile.connection, profile.key, profile.label)
    member = member_from_output_name(source_file.stem)
    content = source_file.read_bytes()

    client.upload_member(profile.dataset, member, content)
    client.verify_member(profile.dataset, member, content)

    if diagnostics is not None:
        diagnostics.append(
            DIAG_UPLOAD_TEMPLATE.format(
                path=source_file, dataset=profile.dataset, member=member
            )
        )
        diagnostics.append(
            DIAG_VERIFIED_TEMPLATE.format(
                dataset=profile.dataset, member=member, size=len(content)
            )
        )
    return profile.dataset, member


def upload_converted_folder(
    folder: Path,
    extension: str = "",
    diagnostics: list[str] | None = None,
) -> list[tuple[str, str]]:
    """Upload every generated program in a folder."""
    profile = build_output_profile()
    suffix = extension or profile.extension

    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Output folder does not exist: {folder}")

    results: list[tuple[str, str]] = []
    for path in sorted(folder.glob(f"*{suffix}")):
        results.append(upload_converted_program(path, profile, diagnostics))
    return results