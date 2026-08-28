"""
DB2 comment readability service.

Improves the readability of generated DB2 comments only, preserving original
business comments exactly. Extracted from the former final fix composer.
"""

from __future__ import annotations

from patterns.final_feedback_fix_patterns import (
    DB2_COLON_COMMENT_BODY_PATTERN,
    DB2_SPACE_COMMENT_BODY_PATTERN,
)
from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)


class Db2CommentReadabilityService:
    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.fixed_format = fixed_format or FixedFormatLineService()

    def apply(self, text: str) -> str:
        if not text:
            return ""

        lines = str(text or "").splitlines()
        output: list[str] = []
        db2_colon_continuation_pending = False

        for line in lines:
            if not line:
                output.append(line)
                db2_colon_continuation_pending = False
                continue

            if self.fixed_format.is_fixed_line(line):
                left, indicator, body, right = self.fixed_format.split(line)

                if indicator != "*":
                    output.append(line)
                    db2_colon_continuation_pending = False
                    continue

                clean_body = str(body or "").rstrip().strip()

                if not clean_body:
                    output.append(line)
                    db2_colon_continuation_pending = False
                    continue

                is_colon = bool(
                    DB2_COLON_COMMENT_BODY_PATTERN.match(clean_body)
                )
                is_space = bool(
                    DB2_SPACE_COMMENT_BODY_PATTERN.match(clean_body)
                )

                if is_colon:
                    normalized = DB2_COLON_COMMENT_BODY_PATTERN.sub(
                        "DB2:", clean_body, count=1
                    ).strip()
                    updated = self._try_build_fixed_comment_line(
                        left=left, right=right, comment_body=normalized
                    )
                    output.append(updated or line)
                    db2_colon_continuation_pending = True
                    continue

                if is_space:
                    normalized = DB2_SPACE_COMMENT_BODY_PATTERN.sub(
                        "DB2 ", clean_body, count=1
                    ).strip()
                    updated = self._try_build_fixed_comment_line(
                        left=left, right=right, comment_body=normalized
                    )
                    output.append(updated or line)
                    db2_colon_continuation_pending = False
                    continue

                if db2_colon_continuation_pending:
                    updated = self._try_build_fixed_comment_line(
                        left=left, right=right, comment_body=clean_body
                    )
                    output.append(updated or line)
                    db2_colon_continuation_pending = False
                    continue

                output.append(line)
                db2_colon_continuation_pending = False
                continue

            stripped = str(line or "").strip()

            if not stripped:
                output.append(line)
                db2_colon_continuation_pending = False
                continue

            is_colon = bool(DB2_COLON_COMMENT_BODY_PATTERN.match(stripped))
            is_space = bool(DB2_SPACE_COMMENT_BODY_PATTERN.match(stripped))

            if is_colon:
                normalized = DB2_COLON_COMMENT_BODY_PATTERN.sub(
                    "DB2:", stripped, count=1
                ).strip()
                output.append(f"* {normalized}")
                db2_colon_continuation_pending = True
                continue

            if is_space:
                normalized = DB2_SPACE_COMMENT_BODY_PATTERN.sub(
                    "DB2 ", stripped, count=1
                ).strip()
                output.append(f"* {normalized}")
                db2_colon_continuation_pending = False
                continue

            if db2_colon_continuation_pending and stripped.startswith("*"):
                continuation = stripped[1:].lstrip()
                output.append(f"* {continuation}")
                db2_colon_continuation_pending = False
                continue

            output.append(line)
            db2_colon_continuation_pending = False

        return "\n".join(output).rstrip() + "\n"

    def _try_build_fixed_comment_line(
        self,
        left: str,
        right: str,
        comment_body: str,
    ) -> str:
        clean_body = str(comment_body or "").strip()

        if not clean_body:
            return ""

        body = f" {clean_body}"

        if len(body) > self.fixed_format.BODY_WIDTH:
            return ""

        return self.fixed_format.build(left, "*", body, right)