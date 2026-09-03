from __future__ import annotations

import re

from patterns.update_record_rename_patterns import (
    COPY_RECORD_PATTERN_TEMPLATE,
    WORD_RECORD_PATTERN_TEMPLATE,
)


class UpdateInputRecordRenamer:
    """Renames original source references to the input record.

    Update-postprocess only. Does not touch retrieval.

    Given the original input-record name and its derived name (e.g.
    VMBD205I -> VMDZ205I from the VM...BD...->VMDZ rule), this pass:
      - renames non-comment executable references (COPY, OF/IN, INITIALIZE,
        READ INTO, MOVE, etc.) from old -> new,
      - removes duplicate COPY <new> lines (keeps the first),
      - never modifies comment lines (indicator '*' in column 7) so REMARKS
        history stays byte-for-byte identical.

    No program, record, or copybook name is hardcoded; old/new come from the
    resolved context.
    """

    def apply(
        self,
        text: str,
        old_name: str,
        new_name: str,
        diagnostics: list[str] | None = None,
    ) -> str:
        if not text:
            return text or ""

        old = str(old_name or "").strip().upper()
        new = str(new_name or "").strip().upper()

        if not old or not new or old == new:
            return text

        word_pattern = re.compile(
            WORD_RECORD_PATTERN_TEMPLATE.format(name=re.escape(old)),
            flags=re.IGNORECASE,
        )
        copy_new_pattern = re.compile(
            COPY_RECORD_PATTERN_TEMPLATE.format(name=re.escape(new)),
            flags=re.IGNORECASE,
        )

        lines = (
            str(text)
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .split("\n")
        )

        output: list[str] = []
        changed = False
        seen_copy_new = False

        for line in lines:
            # Never touch comment / debug / page lines.
            if self._is_comment_or_debug(line):
                output.append(line)
                continue

            body = self._body(line)

            # Rename whole-word occurrences of the old record name.
            new_body = word_pattern.sub(new, body)

            if new_body != body:
                changed = True
                line = self._replace_body(line, new_body)
                body = new_body

            # Deduplicate COPY <new> lines (keep the first only).
            if copy_new_pattern.search(body):
                if seen_copy_new:
                    changed = True
                    continue  # drop the duplicate COPY line
                seen_copy_new = True

            output.append(line)

        if changed and diagnostics is not None:
            diagnostics.append(
                f"Renamed input record references {old} -> {new} "
                "and removed duplicate COPY."
            )

        return "\n".join(output).rstrip() + "\n"

    # ------------------------------------------------------------------ #
    # Fixed-format helpers
    # ------------------------------------------------------------------ #
    def _is_comment_or_debug(self, line: str) -> bool:
        text = str(line or "").rstrip("\n")
        if len(text) >= 7 and text[:6].strip().isdigit():
            return text[6:7] in {"*", "/", "D", "d"}
        stripped = text.strip()
        return (
            stripped.startswith("*")
            or stripped.startswith("/")
            or stripped.upper().startswith("D ")
        )

    def _body(self, line: str) -> str:
        text = str(line or "").rstrip("\n")
        if len(text) >= 72 and text[:6].strip().isdigit():
            return text[7:72].rstrip()
        if len(text) > 6 and text[:6].strip().isdigit():
            body = text[7:] if len(text) > 7 else ""
            if len(body) >= 8 and body[-8:].strip().isdigit():
                body = body[:-8]
            return body.rstrip()
        return text.rstrip()

    def _replace_body(self, line: str, body: str) -> str:
        text = str(line or "").rstrip("\n")
        clean = str(body or "")[:65].ljust(65)
        if len(text) >= 72 and text[:6].strip().isdigit():
            left = text[:6]
            right = text[72:80] if len(text) >= 80 else ""
            return f"{left} {clean} {right}"
        if len(text) > 6 and text[:6].strip().isdigit():
            left = text[:6]
            return f"{left} {clean.rstrip()}"
        return clean.rstrip()