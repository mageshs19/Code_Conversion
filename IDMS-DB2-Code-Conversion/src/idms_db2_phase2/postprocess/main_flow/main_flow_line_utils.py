from __future__ import annotations

from rules.update_restart_rules import (
    MAIN_FLOW_AREA_B_INDENT,
    MAIN_FLOW_BODY_END,
    MAIN_FLOW_BODY_START,
    MAIN_FLOW_COMMENT_INDICATORS,
    MAIN_FLOW_FIXED_BODY_WIDTH,
    MAIN_FLOW_FULL_WIDTH,
    MAIN_FLOW_RIGHT_SEQUENCE_WIDTH,
    MAIN_FLOW_SEQUENCE_WIDTH,
    MAIN_FLOW_TOTAL_WIDTH,
)


class MainFlowLineUtils:
    """Fixed-format line rendering + logical extraction.

    Owns no business rules. Column geometry comes from
    rules/update_restart_rules.py.
    """

    def _line_like(self, *, reference_line: str, body: str) -> str:
        text = str(reference_line or "").rstrip("\n")
        clean_body = str(body or "").strip()

        if (
            len(text) >= MAIN_FLOW_FULL_WIDTH
            and text[:MAIN_FLOW_SEQUENCE_WIDTH].strip().isdigit()
        ):
            left = text[:MAIN_FLOW_SEQUENCE_WIDTH]
            indicator = text[MAIN_FLOW_SEQUENCE_WIDTH] if len(text) > MAIN_FLOW_SEQUENCE_WIDTH else " "
            right = (
                text[MAIN_FLOW_BODY_END:MAIN_FLOW_TOTAL_WIDTH]
                if len(text) >= MAIN_FLOW_TOTAL_WIDTH
                else ""
            )
            body_area = f"{MAIN_FLOW_AREA_B_INDENT}{clean_body}"
            return (
                f"{left}{indicator}"
                f"{body_area[:MAIN_FLOW_FIXED_BODY_WIDTH].ljust(MAIN_FLOW_FIXED_BODY_WIDTH)}"
                f"{right}"
            )

        if (
            len(text) > MAIN_FLOW_SEQUENCE_WIDTH
            and text[:MAIN_FLOW_SEQUENCE_WIDTH].strip().isdigit()
        ):
            left = text[:MAIN_FLOW_SEQUENCE_WIDTH]
            indicator = text[MAIN_FLOW_SEQUENCE_WIDTH] if len(text) > MAIN_FLOW_SEQUENCE_WIDTH else " "
            body_area = f"{MAIN_FLOW_AREA_B_INDENT}{clean_body}"
            return f"{left}{indicator}{body_area[:MAIN_FLOW_FIXED_BODY_WIDTH].rstrip()}"

        return f"{MAIN_FLOW_AREA_B_INDENT}{clean_body}"

    def _logical(self, line: str) -> str:
        text = str(line or "").rstrip("\n")

        if (
            len(text) >= MAIN_FLOW_FULL_WIDTH
            and text[:MAIN_FLOW_SEQUENCE_WIDTH].strip().isdigit()
        ):
            return text[MAIN_FLOW_BODY_START:MAIN_FLOW_BODY_END].strip()

        if (
            len(text) > MAIN_FLOW_SEQUENCE_WIDTH
            and text[:MAIN_FLOW_SEQUENCE_WIDTH].strip().isdigit()
        ):
            body = text[MAIN_FLOW_SEQUENCE_WIDTH:]
            if body[:1] in MAIN_FLOW_COMMENT_INDICATORS:
                return body.strip()
            if (
                len(body) >= MAIN_FLOW_RIGHT_SEQUENCE_WIDTH
                and body[-MAIN_FLOW_RIGHT_SEQUENCE_WIDTH:].strip().isdigit()
            ):
                body = body[:-MAIN_FLOW_RIGHT_SEQUENCE_WIDTH]
            return body.strip()

        return text.strip()