# LOCATION: zowe/zowe_libraries.py
# ACTION: REPLACE ENTIRE FILE
"""Member lookup across an ordered library list.

A member is taken from the FIRST library that holds it.
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
    """Searches one artifact's libraries. Caches each library listing."""

    artifact: str
    label: str = ""
    libraries: list[str] = field(default_factory=list)
    _client: ZoweClient | None = None
    _members: dict[str, set[str]] = field(default_factory=dict)

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

    def _members_of(self, dataset: str) -> set[str]:
        """Member names of one library. A failed listing is an empty set."""
        if dataset in self._members:
            return self._members[dataset]

        try:
            names = {m.upper() for m in self.client.list_members(dataset)}
        except (requests.HTTPError, requests.RequestException, ValueError) as exc:
            logger.warning("%s listing failed for %s: %s", self.label, dataset, exc)
            names = set()

        self._members[dataset] = names
        return names

    def locate(self, member: str) -> str:
        """First library holding the member, or an empty string."""
        wanted = str(member or "").strip().upper()
        if not wanted:
            return ""
        for dataset in self.libraries:
            if wanted in self._members_of(dataset):
                return dataset
        return ""

    def download(self, member: str) -> tuple[str, bytes]:
        """(dataset, content). Dataset is empty when not found anywhere."""
        dataset = self.locate(member)
        if not dataset:
            return "", b""
        return dataset, self.client.download_member(dataset, member)