# LOCATION: zowe/zowe_client.py
# ACTION: REPLACE ENTIRE FILE
"""REST Files calls. One client instance per connection.

LOOKUP POLICY

A member is located by PROBING it directly, never by listing the whole
library. A library larger than the z/OSMF item limit silently truncates
its member list, and a truncated list looks exactly like a missing
member. list_members is kept for diagnostics only.
"""

from __future__ import annotations

import logging

import requests
from requests.auth import HTTPBasicAuth

from zowe.zowe_patterns import (
    DATASET_NAME_PATTERN,
    MEMBER_PATH_PATTERN,
    UNSAFE_FILENAME_CHAR_PATTERN,
)
from zowe.zowe_rules import (
    CSRF_HEADER,
    DATA_TYPE_HEADER,
    HTTP_OK,
    LOG_CONNECTION,
    LOG_DOWNLOAD,
    LOG_MEMBER_COUNT,
    LOG_UPLOAD,
    MAX_ITEMS_HEADER,
    MEMBER_NAME_MAX_LENGTH,
    TEXT_CONTENT_TYPE,
    ZOWE_ERROR_MESSAGES,
)
from zowe.zowe_settings import ZoweConnection

logger = logging.getLogger("idms_db2_zowe")


class ZoweClient:
    """Talks to exactly one endpoint."""

    def __init__(self, connection: ZoweConnection, artifact: str, label: str) -> None:
        self.connection = connection
        self.artifact = artifact
        self.label = label
        self._validate()
        logger.info(LOG_CONNECTION, label, connection.host, connection.port)

    # ---- guards ----
    def _validate(self) -> None:
        if not self.connection.host:
            raise ValueError(
                ZOWE_ERROR_MESSAGES["missing_host"].format(
                    label=self.label, artifact=self.artifact
                )
            )
        if not self.connection.user or not self.connection.password:
            raise ValueError(
                ZOWE_ERROR_MESSAGES["missing_credentials"].format(
                    label=self.label, artifact=self.artifact
                )
            )

    @staticmethod
    def library_name(dataset: str) -> str:
        normalized = str(dataset or "").strip().upper()
        if MEMBER_PATH_PATTERN.search(normalized):
            raise ValueError(
                ZOWE_ERROR_MESSAGES["member_path_not_allowed"].format(dataset=dataset)
            )
        if not DATASET_NAME_PATTERN.match(normalized):
            raise ValueError(
                ZOWE_ERROR_MESSAGES["invalid_dataset"].format(dataset=dataset)
            )
        return normalized

    @staticmethod
    def member_name(name: str) -> str:
        cleaned = UNSAFE_FILENAME_CHAR_PATTERN.sub("_", str(name or ""))
        cleaned = cleaned.strip("_").upper()
        if not cleaned:
            raise ValueError(f"Cannot derive a PDS member name from: {name}")
        return cleaned[:MEMBER_NAME_MAX_LENGTH]

    # ---- helpers ----
    def _auth(self) -> HTTPBasicAuth:
        return HTTPBasicAuth(self.connection.user, self.connection.password)

    def _member_url(self, dataset: str, member: str) -> str:
        return f"{self.connection.base_url}/{dataset}({member})"

    def _members_url(self, dataset: str) -> str:
        return f"{self.connection.base_url}/{dataset}/member"

    def _get_member(self, dataset: str, member: str) -> requests.Response:
        """One GET on a member. Status is never raised on."""
        dataset = self.library_name(dataset)
        response = requests.get(
            self._member_url(dataset, member),
            headers={**CSRF_HEADER, **DATA_TYPE_HEADER},
            auth=self._auth(),
            verify=self.connection.verify_tls,
            timeout=self.connection.timeout_seconds,
        )
        logger.info(LOG_DOWNLOAD, dataset, member, response.status_code)
        return response

    # ---- lookup ----
    def member_exists(self, dataset: str, member: str) -> tuple[bool, int]:
        """Probe ONE member. Returns (found, http_status)."""
        response = self._get_member(dataset, member)
        return response.status_code == HTTP_OK, response.status_code

    def fetch_member(self, dataset: str, member: str) -> tuple[bytes, int]:
        """Content and status. Empty bytes when the member is absent."""
        response = self._get_member(dataset, member)
        if response.status_code == HTTP_OK:
            return response.content, HTTP_OK
        return b"", response.status_code

    # ---- operations ----
    def download_member(self, dataset: str, member: str) -> bytes:
        """Strict download. Raises on any non-200 status."""
        response = self._get_member(dataset, member)
        response.raise_for_status()
        return response.content

    def list_members(self, dataset: str) -> list[str]:
        """Diagnostic only. Never used to decide whether a member exists."""
        dataset = self.library_name(dataset)
        response = requests.get(
            self._members_url(dataset),
            headers={**CSRF_HEADER, **MAX_ITEMS_HEADER},
            auth=self._auth(),
            verify=self.connection.verify_tls,
            timeout=self.connection.timeout_seconds,
        )
        response.raise_for_status()
        items = response.json().get("items", []) or []
        members = sorted(item["member"] for item in items if item.get("member"))
        logger.info(LOG_MEMBER_COUNT, self.label, len(members))
        if not members:
            raise ValueError(ZOWE_ERROR_MESSAGES["no_members"].format(dataset=dataset))
        return members

    def upload_member(self, dataset: str, member: str, content: bytes) -> int:
        dataset = self.library_name(dataset)
        response = requests.put(
            self._member_url(dataset, member),
            headers={**CSRF_HEADER, "Content-Type": TEXT_CONTENT_TYPE},
            auth=self._auth(),
            data=content,
            verify=self.connection.verify_tls,
            timeout=self.connection.timeout_seconds,
        )
        logger.info(LOG_UPLOAD, dataset, member, response.status_code)
        response.raise_for_status()
        return response.status_code

    def verify_member(self, dataset: str, member: str, expected: bytes) -> None:
        retrieved = self.download_member(dataset, member)
        if retrieved != expected:
            raise ValueError(
                ZOWE_ERROR_MESSAGES["verify_mismatch"].format(
                    dataset=self.library_name(dataset),
                    member=member,
                    sent=len(expected),
                    received=len(retrieved),
                )
            )