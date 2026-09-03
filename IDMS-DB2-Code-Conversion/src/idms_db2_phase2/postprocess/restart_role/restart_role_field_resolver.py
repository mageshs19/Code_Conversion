from __future__ import annotations

from rules.update_restart_rules import (
    RESTART_DCLGEN_ROLE_TOKENS,
    RESTART_PAYLOAD_FALLBACK_TOKEN_KEY,
    RESTART_PAYLOAD_TOKEN_KEY,
    RESTART_VARCHAR_SUFFIXES,
)


class RestartRoleFieldResolver:
    """Resolves restart columns, fields, and payload child fields.

    Uses the token-driven matcher; owns no hardcoded restart names.
    Depends on the host class for ``self.matcher`` and ``self.row_mapper``.
    """

    def _payload_exclude_tokens(self) -> list[str]:
        return [
            RESTART_VARCHAR_SUFFIXES["length"],
            RESTART_VARCHAR_SUFFIXES["text"],
        ]

    def _resolve_payload_group(self, rows: list[dict[str, str]]) -> str:
        exclude = self._payload_exclude_tokens()

        payload_group = self.matcher.find_optional_field(
            rows=rows,
            tokens=RESTART_DCLGEN_ROLE_TOKENS[RESTART_PAYLOAD_TOKEN_KEY],
            fallback_tokens=RESTART_DCLGEN_ROLE_TOKENS[
                RESTART_PAYLOAD_FALLBACK_TOKEN_KEY
            ],
            exclude_tokens=exclude,
        )
        if payload_group:
            return payload_group

        payload_column = self.matcher.find_optional_col(
            rows=rows,
            tokens=RESTART_DCLGEN_ROLE_TOKENS[RESTART_PAYLOAD_TOKEN_KEY],
            fallback_tokens=RESTART_DCLGEN_ROLE_TOKENS[
                RESTART_PAYLOAD_FALLBACK_TOKEN_KEY
            ],
            exclude_tokens=exclude,
        )
        if payload_column and hasattr(self.row_mapper, "column_to_cobol_field"):
            return self.row_mapper.column_to_cobol_field(payload_column)
        if payload_column:
            return payload_column.replace("_", "-")

        return self.matcher.find_field(
            rows=rows,
            tokens=RESTART_DCLGEN_ROLE_TOKENS[RESTART_PAYLOAD_TOKEN_KEY],
            fallback_tokens=RESTART_DCLGEN_ROLE_TOKENS[
                RESTART_PAYLOAD_FALLBACK_TOKEN_KEY
            ],
            exclude_tokens=exclude,
        )

    def _resolve_payload_child_field(
        self,
        *,
        rows: list[dict[str, str]],
        payload_group: str,
        token_key: str,
        fallback_token_key: str,
        suffix_key: str,
    ) -> str:
        suffix = RESTART_VARCHAR_SUFFIXES[suffix_key]

        explicit_child = self.matcher.find_optional_field(
            rows=rows,
            tokens=RESTART_DCLGEN_ROLE_TOKENS[token_key],
            fallback_tokens=RESTART_DCLGEN_ROLE_TOKENS[fallback_token_key],
        )

        if explicit_child:
            if explicit_child == payload_group:
                return self._derive_varchar_field(
                    payload_group=payload_group, suffix_key=suffix_key
                )
            if explicit_child.endswith(suffix):
                return explicit_child
            if payload_group and explicit_child.startswith(payload_group):
                return explicit_child

        return self._derive_varchar_field(
            payload_group=payload_group, suffix_key=suffix_key
        )

    def _derive_varchar_field(self, *, payload_group: str, suffix_key: str) -> str:
        if not payload_group:
            return ""
        suffix = RESTART_VARCHAR_SUFFIXES[suffix_key]
        if payload_group.endswith(suffix):
            return payload_group
        return f"{payload_group}{suffix}"

    def _find_column(
        self, *, rows: list[dict[str, str]], token_key: str, fallback_token_key: str
    ) -> str:
        return self.matcher.find_col(
            rows=rows,
            tokens=RESTART_DCLGEN_ROLE_TOKENS[token_key],
            fallback_tokens=RESTART_DCLGEN_ROLE_TOKENS[fallback_token_key],
        )

    def _find_field(
        self, *, rows: list[dict[str, str]], token_key: str, fallback_token_key: str
    ) -> str:
        return self.matcher.find_field(
            rows=rows,
            tokens=RESTART_DCLGEN_ROLE_TOKENS[token_key],
            fallback_tokens=RESTART_DCLGEN_ROLE_TOKENS[fallback_token_key],
        )