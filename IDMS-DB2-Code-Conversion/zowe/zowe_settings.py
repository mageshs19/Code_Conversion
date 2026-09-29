# LOCATION: zowe/zowe_settings.py
# ACTION: REPLACE ENTIRE FILE
"""Per-artifact connection and library resolution.

Program, Copybook, DCLGEN and Subschema each carry their own host, port,
credentials, TLS policy and ORDERED library list. No Retrieval / Update
split exists anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from zowe.zowe_env import setting, setting_bool, setting_int
from zowe.zowe_rules import (
    APPLICATION_PLACEHOLDER,
    ARTIFACT_EXTENSIONS,
    ARTIFACT_LABELS,
    ARTIFACT_OUTPUT,
    BASE_URL_TEMPLATE,
    DEFAULT_APPLICATION,
    DEFAULT_LANDING_SUBFOLDERS,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_VERIFY_TLS,
    LIBRARY_SEPARATOR,
    MANDATORY_ARTIFACTS,
    NAME_APPLICATION,
    NAME_DATASET,
    NAME_HOST,
    NAME_LANDING,
    NAME_LIBRARIES,
    NAME_PASSWORD,
    NAME_PORT,
    NAME_READ_ONLY,
    NAME_TIMEOUT,
    NAME_USER,
    NAME_VERIFY_TLS,
    ZOWE_ARTIFACT_KEYS,
    ZOWE_ERROR_MESSAGES,
)
from zowe.zowe_workspace import workspace_root


# =====================================================================
# Application code and {XY} expansion
# =====================================================================
def application_code() -> str:
    """XY - first two letters of the application being migrated."""
    value = setting("", NAME_APPLICATION, DEFAULT_APPLICATION)
    return value.strip().upper() or DEFAULT_APPLICATION


def expand(template: str) -> str:
    """BAS.{XY}.CPY -> BAS.VM.CPY"""
    text = str(template or "").replace(APPLICATION_PLACEHOLDER, application_code())
    return text.strip().upper()


# =====================================================================
# Value objects
# =====================================================================
@dataclass(frozen=True)
class ZoweConnection:
    """One endpoint. Two artifacts may point at different systems."""

    host: str
    port: int
    user: str
    password: str
    verify_tls: bool
    timeout_seconds: int

    @property
    def base_url(self) -> str:
        return BASE_URL_TEMPLATE.format(host=self.host, port=self.port)

    @property
    def fingerprint(self) -> str:
        return f"{self.host}:{self.port}:{self.user}"


@dataclass(frozen=True)
class ArtifactProfile:
    """One artifact: connection, ordered libraries, landing folder."""

    key: str
    label: str
    connection: ZoweConnection
    libraries: tuple[str, ...] = field(default_factory=tuple)
    dataset: str = ""
    landing_dir: Path = field(default_factory=workspace_root)
    extension: str = ""
    mandatory: bool = False
    read_only: bool = False

    @property
    def configured(self) -> bool:
        return bool(self.libraries) or bool(self.dataset)


# =====================================================================
# Resolution
# =====================================================================
def _connection(artifact: str) -> ZoweConnection:
    return ZoweConnection(
        host=setting(artifact, NAME_HOST),
        port=setting_int(artifact, NAME_PORT, DEFAULT_PORT),
        user=setting(artifact, NAME_USER),
        password=setting(artifact, NAME_PASSWORD),
        verify_tls=setting_bool(artifact, NAME_VERIFY_TLS, DEFAULT_VERIFY_TLS),
        timeout_seconds=setting_int(artifact, NAME_TIMEOUT, DEFAULT_TIMEOUT_SECONDS),
    )


def artifact_connection(artifact: str) -> ZoweConnection:
    """Public accessor so other modules do not rebuild whole profiles."""
    return _connection(artifact)


def artifact_libraries(artifact: str) -> tuple[str, ...]:
    """Ordered, de-duplicated library list. Empty when unset."""
    raw = setting(artifact, NAME_LIBRARIES)
    if not raw:
        return ()

    out: list[str] = []
    for token in raw.split(LIBRARY_SEPARATOR):
        dataset = expand(token)
        if dataset and dataset not in out:
            out.append(dataset)
    return tuple(out)


def require_libraries(artifact: str) -> tuple[str, ...]:
    libraries = artifact_libraries(artifact)
    if not libraries:
        raise ValueError(
            ZOWE_ERROR_MESSAGES["no_libraries"].format(
                label=ARTIFACT_LABELS[artifact], artifact=artifact
            )
        )
    return libraries


def landing_root() -> Path:
    return workspace_root()


def _landing_dir(artifact: str) -> Path:
    configured = setting(artifact, NAME_LANDING)
    sub = configured or DEFAULT_LANDING_SUBFOLDERS.get(artifact, artifact.title())

    candidate = Path(sub)
    return candidate if candidate.is_absolute() else workspace_root() / sub


def _profile(artifact: str) -> ArtifactProfile:
    return ArtifactProfile(
        key=artifact,
        label=ARTIFACT_LABELS[artifact],
        connection=_connection(artifact),
        libraries=artifact_libraries(artifact),
        landing_dir=_landing_dir(artifact),
        extension=ARTIFACT_EXTENSIONS[artifact],
        mandatory=artifact in MANDATORY_ARTIFACTS,
    )


def build_profiles() -> tuple[ArtifactProfile, ...]:
    """The four input artifacts, each resolved independently."""
    return tuple(_profile(artifact) for artifact in ZOWE_ARTIFACT_KEYS)


def build_output_profile() -> ArtifactProfile:
    """Write-back target. A single dataset, not a library list."""
    return ArtifactProfile(
        key=ARTIFACT_OUTPUT,
        label=ARTIFACT_LABELS[ARTIFACT_OUTPUT],
        connection=_connection(ARTIFACT_OUTPUT),
        dataset=expand(setting(ARTIFACT_OUTPUT, NAME_DATASET)),
        landing_dir=_landing_dir(ARTIFACT_OUTPUT),
        extension=ARTIFACT_EXTENSIONS[ARTIFACT_OUTPUT],
        mandatory=False,
        read_only=setting_bool(ARTIFACT_OUTPUT, NAME_READ_ONLY, False),
    )