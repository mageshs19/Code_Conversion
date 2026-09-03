from __future__ import annotations

from rules.update_business_sql_rules import (
    ACTIVE_INDICATOR,
    AREA_B_INDENT,
    BODY_END_COLUMN,
    BODY_START_COLUMN,
    COMMENT_INDICATORS,
    FIXED_BODY_WIDTH,
    FULL_LINE_WIDTH,
    INDICATOR_COLUMN,
    RIGHT_SEQUENCE_WIDTH,
    SEQUENCE_AREA_WIDTH,
    TOTAL_LINE_WIDTH,
)


class UpdateBusinessSqlLineRenderer:
    """Fixed-format line rendering + logical-line extraction.

    Owns no regex and no business rules. Column geometry and indents come
    from rules/update_business_sql_rules.py.
    """

    def _active_line_like(self, *, reference_line: str, body: str) -> str:
        return self._line_like(
            reference_line=reference_line,
            body=body,
            force_indicator=ACTIVE_INDICATOR,
        )

    def _line_like(
        self,
        *,
        reference_line: str,
        body: str,
        force_indicator: str | None = None,
    ) -> str:
        text = str(reference_line or "").rstrip("\n")
        clean_body = str(body or "").strip()

        if len(text) >= FULL_LINE_WIDTH and text[:SEQUENCE_AREA_WIDTH].strip().isdigit():
            left = text[:SEQUENCE_AREA_WIDTH]
            indicator = self._indicator_for(text, force_indicator)
            right = (
                text[BODY_END_COLUMN:TOTAL_LINE_WIDTH]
                if len(text) >= TOTAL_LINE_WIDTH
                else ""
            )
            body_area = f"{AREA_B_INDENT}{clean_body}"
            return (
                f"{left}{indicator}"
                f"{body_area[:FIXED_BODY_WIDTH].ljust(FIXED_BODY_WIDTH)}"
                f"{right}"
            )

        if len(text) > SEQUENCE_AREA_WIDTH and text[:SEQUENCE_AREA_WIDTH].strip().isdigit():
            left = text[:SEQUENCE_AREA_WIDTH]
            indicator = self._indicator_for(text, force_indicator)
            body_area = f"{AREA_B_INDENT}{clean_body}"
            return f"{left}{indicator}{body_area[:FIXED_BODY_WIDTH].rstrip()}"

        return f"{AREA_B_INDENT}{clean_body}"

    def _indicator_for(self, text: str, force_indicator: str | None) -> str:
        if force_indicator is not None:
            return force_indicator
        return text[SEQUENCE_AREA_WIDTH] if len(text) > SEQUENCE_AREA_WIDTH else " "

    def _is_comment_line(self, line: str) -> bool:
        text = str(line or "").rstrip("\n")

        if len(text) >= INDICATOR_COLUMN and text[:SEQUENCE_AREA_WIDTH].strip().isdigit():
            return text[SEQUENCE_AREA_WIDTH:INDICATOR_COLUMN] in COMMENT_INDICATORS

        stripped = text.strip()
        return any(stripped.startswith(ind) for ind in COMMENT_INDICATORS)

    def _logical(self, line: str) -> str:
        text = str(line or "").rstrip("\n")

        if len(text) >= FULL_LINE_WIDTH and text[:SEQUENCE_AREA_WIDTH].strip().isdigit():
            return text[BODY_START_COLUMN:BODY_END_COLUMN].strip()

        if len(text) > SEQUENCE_AREA_WIDTH and text[:SEQUENCE_AREA_WIDTH].strip().isdigit():
            body = text[BODY_START_COLUMN:] if len(text) > BODY_START_COLUMN else ""
            if (
                len(body) >= RIGHT_SEQUENCE_WIDTH
                and body[-RIGHT_SEQUENCE_WIDTH:].strip().isdigit()
            ):
                body = body[:-RIGHT_SEQUENCE_WIDTH]
            return body.strip()

        return text.strip()