from __future__ import annotations

from typing import Optional

from idms_db2_phase2.postprocess.update_metadata_models import compact


class UpdateRestartDclgenMatcher:
    """
    Finds restart columns or COBOL host fields using token matching.

    This class contains generic matching logic only.
    Business tokens are supplied from rules/update_restart_rules.py.

    Important:
    - Restart role matching must be strict enough to avoid resolving one role
      to another field.
    - Example: NM-ID-RS-PROGRAM must not match status just because it contains
      ID and RS.
    - Therefore all configured tokens must be present for a match.
    """

    def find_optional_col(
        self,
        *,
        rows: list[dict[str, str]],
        tokens: list[str],
        fallback_tokens: Optional[list[str]] = None,
        exclude_tokens: Optional[list[str]] = None,
    ) -> str:
        try:
            return self.find_col(
                rows=rows,
                tokens=tokens,
                fallback_tokens=fallback_tokens,
                exclude_tokens=exclude_tokens,
            )
        except ValueError:
            return ""

    def find_optional_field(
        self,
        *,
        rows: list[dict[str, str]],
        tokens: list[str],
        fallback_tokens: Optional[list[str]] = None,
        exclude_tokens: Optional[list[str]] = None,
    ) -> str:
        try:
            return self.find_field(
                rows=rows,
                tokens=tokens,
                fallback_tokens=fallback_tokens,
                exclude_tokens=exclude_tokens,
            )
        except ValueError:
            return ""

    def find_col(
        self,
        *,
        rows: list[dict[str, str]],
        tokens: list[str],
        fallback_tokens: Optional[list[str]] = None,
        exclude_tokens: Optional[list[str]] = None,
    ) -> str:
        return self.find_by_key(
            rows=rows,
            key="column",
            tokens=tokens,
            fallback_tokens=fallback_tokens,
            exclude_tokens=exclude_tokens,
        )

    def find_field(
        self,
        *,
        rows: list[dict[str, str]],
        tokens: list[str],
        fallback_tokens: Optional[list[str]] = None,
        exclude_tokens: Optional[list[str]] = None,
    ) -> str:
        return self.find_by_key(
            rows=rows,
            key="field",
            tokens=tokens,
            fallback_tokens=fallback_tokens,
            exclude_tokens=exclude_tokens,
        )

    def find_by_key(
        self,
        *,
        rows: list[dict[str, str]],
        key: str,
        tokens: list[str],
        fallback_tokens: Optional[list[str]] = None,
        exclude_tokens: Optional[list[str]] = None,
    ) -> str:
        fallback_tokens = fallback_tokens or []
        exclude_tokens = exclude_tokens or []

        scored: list[tuple[int, int, str]] = []

        for index, row in enumerate(rows):
            value = str(row.get(key, "") or "").strip()

            if not value:
                continue

            searchable = self._searchable_row_text(row=row, primary_key=key)

            if self._has_excluded_token(
                searchable=searchable,
                exclude_tokens=exclude_tokens,
            ):
                continue

            score = self._match_score(
                searchable=searchable,
                tokens=tokens,
                fallback_tokens=fallback_tokens,
            )

            if score > 0:
                scored.append((score, index, value))

        if not scored:
            raise ValueError(f"Unable to resolve restart field using tokens {tokens}")

        scored.sort(
            key=lambda item: (-item[0], item[1]),
        )

        return scored[0][2]

    def score_rows_for_restart(
        self,
        *,
        rows: list[dict[str, str]],
        token_sets: list[list[str]],
    ) -> int:
        score = 0

        for row in rows:
            searchable = self._searchable_row_text(row=row, primary_key="field")

            for tokens in token_sets:
                compact_tokens = [compact(token) for token in tokens if compact(token)]

                if self._token_set_found(
                    searchable=searchable,
                    tokens=tokens,
                ):
                    score += len(compact_tokens)

        return score

    def _searchable_row_text(
        self,
        *,
        row: dict[str, str],
        primary_key: str,
    ) -> str:
        parts = [
            row.get(primary_key, ""),
            row.get("field", ""),
            row.get("column", ""),
            row.get("table_name", ""),
            row.get("include_name", ""),
            row.get("host_record", ""),
            row.get("source_label", ""),
        ]

        return compact(" ".join(str(part or "") for part in parts))

    def _match_score(
        self,
        *,
        searchable: str,
        tokens: list[str],
        fallback_tokens: list[str],
    ) -> int:
        primary_tokens = [compact(token) for token in tokens if compact(token)]

        if self._token_set_found(
            searchable=searchable,
            tokens=tokens,
        ):
            return len(primary_tokens) * 10

        fallback_compact_tokens = [
            compact(token)
            for token in fallback_tokens
            if compact(token)
        ]

        if self._token_set_found(
            searchable=searchable,
            tokens=fallback_tokens,
        ):
            return len(fallback_compact_tokens)

        return 0

    def _token_set_found(
        self,
        *,
        searchable: str,
        tokens: list[str],
    ) -> bool:
        compact_tokens = [compact(token) for token in tokens if compact(token)]

        if not compact_tokens:
            return False

        return all(token in searchable for token in compact_tokens)

    def _has_excluded_token(
        self,
        *,
        searchable: str,
        exclude_tokens: list[str],
    ) -> bool:
        compact_tokens = [compact(token) for token in exclude_tokens if compact(token)]

        if not compact_tokens:
            return False

        return any(token in searchable for token in compact_tokens)