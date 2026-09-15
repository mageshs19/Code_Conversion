# LOCATION: src/idms_db2_phase2/generators/cursor_paragraph/cursor_perform_rewriter.py
# ACTION: CREATE NEW FILE

"""Rewrites PERFORM targets onto generated cursor paragraph names.

Also renames legacy SQL-ERROR references to SQLERROR. This class owns no
regex definitions: every pattern lives in patterns/cursor_paragraph_patterns.py.
"""

from __future__ import annotations

import re

from patterns.cursor_paragraph_patterns import (
    LEGACY_PERFORM_PATTERN_TEMPLATE,
    LEGACY_SQL_ERROR_HEADER_PATTERN,
    LEGACY_SQL_ERROR_HEADER_REPLACEMENT,
    LEGACY_SQL_ERROR_PERFORM_PATTERN,
    NUMBERED_PERFORM_PATTERN_TEMPLATE,
    PERFORM_REPLACEMENT_TEMPLATE,
    UNNUMBERED_PERFORM_PATTERN_TEMPLATE,
)
from rules.cursor_paragraph_rules import (
    CURSOR_OPERATIONS,
    SQL_ERROR_PARAGRAPH_NAME,
)

LEGACY_SPEC_KEYS = (
    ("old_open_paragraph", "open_paragraph"),
    ("old_fetch_paragraph", "fetch_paragraph"),
    ("old_close_paragraph", "close_paragraph"),
)

SPEC_KEY_BY_OPERATION = {
    "OPEN": "open_paragraph",
    "FETCH": "fetch_paragraph",
    "CLOSE": "close_paragraph",
}


class CursorPerformRewriter:

    def rewrite(
        self,
        text: str,
        cursor_specs: list[dict[str, object]],
    ) -> str:
        updated = str(text or "")

        for spec in cursor_specs:
            cursor_name = str(spec.get("cursor_name", "")).strip()

            if not cursor_name:
                continue

            for operation in CURSOR_OPERATIONS:
                target_paragraph = str(
                    spec.get(SPEC_KEY_BY_OPERATION[operation], "")
                ).strip()

                if not target_paragraph:
                    continue

                updated = self._replace_unnumbered(
                    text=updated,
                    operation=operation,
                    cursor_name=cursor_name,
                    target_paragraph=target_paragraph,
                )

                updated = self._replace_numbered(
                    text=updated,
                    operation=operation,
                    cursor_name=cursor_name,
                    target_paragraph=target_paragraph,
                )

            updated = self._replace_legacy_spec(
                text=updated,
                spec=spec,
            )

        return updated

    def normalize_sql_error_references(
        self,
        text: str,
    ) -> str:
        """Rename SQL-ERROR to SQLERROR without changing termination.

        The original terminator is carried through unchanged. Forcing a
        period breaks any PERFORM that sits inside an EVALUATE block.
        """
        updated = str(text or "")

        updated = LEGACY_SQL_ERROR_PERFORM_PATTERN.sub(
            lambda match: (
                f"PERFORM {SQL_ERROR_PARAGRAPH_NAME}"
                + (match.group("dot") or "")
            ),
            updated,
        )

        updated = LEGACY_SQL_ERROR_HEADER_PATTERN.sub(
            LEGACY_SQL_ERROR_HEADER_REPLACEMENT,
            updated,
        )

        return updated

    def _replace_unnumbered(
        self,
        text: str,
        operation: str,
        cursor_name: str,
        target_paragraph: str,
    ) -> str:
        pattern = re.compile(
            UNNUMBERED_PERFORM_PATTERN_TEMPLATE.format(
                operation=re.escape(operation),
                cursor=re.escape(cursor_name),
            ),
            flags=re.IGNORECASE,
        )

        return pattern.sub(
            PERFORM_REPLACEMENT_TEMPLATE.format(paragraph=target_paragraph),
            text,
        )

    def _replace_numbered(
        self,
        text: str,
        operation: str,
        cursor_name: str,
        target_paragraph: str,
    ) -> str:
        pattern = re.compile(
            NUMBERED_PERFORM_PATTERN_TEMPLATE.format(
                operation=re.escape(operation),
                cursor=re.escape(cursor_name),
            ),
            flags=re.IGNORECASE,
        )

        return pattern.sub(
            PERFORM_REPLACEMENT_TEMPLATE.format(paragraph=target_paragraph),
            text,
        )

    def _replace_legacy_spec(
        self,
        text: str,
        spec: dict[str, object],
    ) -> str:
        updated = str(text or "")

        for old_key, new_key in LEGACY_SPEC_KEYS:
            old_paragraph = str(spec.get(old_key, "")).strip()
            new_paragraph = str(spec.get(new_key, "")).strip()

            if not old_paragraph or not new_paragraph:
                continue

            if old_paragraph == new_paragraph:
                continue

            pattern = re.compile(
                LEGACY_PERFORM_PATTERN_TEMPLATE.format(
                    paragraph=re.escape(old_paragraph),
                ),
                flags=re.IGNORECASE,
            )

            updated = pattern.sub(
                PERFORM_REPLACEMENT_TEMPLATE.format(
                    paragraph=new_paragraph,
                ),
                updated,
            )

        return updated