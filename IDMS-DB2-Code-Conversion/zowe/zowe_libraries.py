# LOCATION: zowe/zowe_libraries.py
# ACTION: REPLACE ENTIRE FILE
"""Member lookup across an ordered library list.

A member is taken from the FIRST library that holds it.

The lookup PROBES the member directly rather than listing the library.
A library larger than the z/OSMF item limit truncates its member list,
and a truncated list is indistinguishable from a missing member.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import requests

from zowe.zowe_client import ZoweClient
from zowe.zowe_rules import ARTIFACT_LABELS
from zowe.zowe_settings import (
    ZoweConnection,
    application_code,
    artifact_connection,
    expand,
    require_libraries,
)

logger = logging.getLogger("idms_db2_zowe")

__all__ = [
    "LibrarySearch",
    "application_code",
    "expand",
    "libraries_for",
]


def libraries_for(artifact: str) -> list[str]:
    return list(require_libraries(artifact))


@dataclass
class LibrarySearch:
    """Searches one artifact's libraries, member by member."""

    artifact: str
    label: str = ""
    libraries: list[str] = field(default_factory=list)
    _client: ZoweClient | None = None
    # member -> {dataset: http status} for the last failed search
    attempts: dict[str, dict[str, int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.label = self.label or ARTIFACT_LABELS[self.artifact]
        if not self.libraries:
            self.libraries = libraries_for(self.artifact)

    @property
    def client(self) -> ZoweClient:
        if self._client is None:
            connection: ZoweConnection = artifact_connection(self.artifact)
            self._client = ZoweClient(connection, self.artifact, self.label)
        return self._client

    def locate(self, member: str) -> str:
        """First library holding the member, or an empty string."""
        wanted = str(member or "").strip().upper()
        if not wanted:
            return ""

        statuses: dict[str, int] = {}
        for dataset in self.libraries:
            try:
                found, status = self.client.member_exists(dataset, wanted)
            except (requests.RequestException, ValueError) as exc:
                logger.warning("%s probe failed on %s: %s", self.label, dataset, exc)
                statuses[dataset] = -1
                continue

            statuses[dataset] = status
            if found:
                return dataset

        self.attempts[wanted] = statuses
        return ""

    def download(self, member: str) -> tuple[str, bytes]:
        """(dataset, content). Dataset is empty when not found anywhere."""
        wanted = str(member or "").strip().upper()
        if not wanted:
            return "", b""

        statuses: dict[str, int] = {}
        for dataset in self.libraries:
            try:
                content, status = self.client.fetch_member(dataset, wanted)
            except (requests.RequestException, ValueError) as exc:
                logger.warning("%s fetch failed on %s: %s", self.label, dataset, exc)
                statuses[dataset] = -1
                continue

            statuses[dataset] = status
            if status == 200:
                return dataset, content

        self.attempts[wanted] = statuses
        return "", b""

    def why_not_found(self, member: str) -> str:
        """Per-library HTTP status for the last failed lookup."""
        statuses = self.attempts.get(str(member or "").strip().upper(), {})
        if not statuses:
            return ", ".join(self.libraries)
        return ", ".join(
            f"{dataset} (HTTP {status})" for dataset, status in statuses.items()
        )

    def list_members(self, dataset: str) -> list[str]:
        """Diagnostic only. Never used for lookup."""
        return self.client.list_members(expand(dataset))