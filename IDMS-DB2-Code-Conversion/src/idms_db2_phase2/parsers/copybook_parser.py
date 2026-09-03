"""
Parses COBOL copybook fields.

Supports:
- unsequenced copybook text
- fixed-format copybooks with left sequence numbers
- fixed-format copybooks with right sequence numbers
- multi-line logical COBOL data declarations

Parser remains generic. It does not hardcode copybook names, program names,
record names, or business field names.
"""

from __future__ import annotations

import re

from idms_db2_phase2.domain.models import CopybookField
from idms_db2_phase2.parsers.base_text_parser import BaseTextParser
from patterns.copybook_patterns import (
    COPYBOOK_COMMENT_OR_SKIP_PATTERN,
    COPYBOOK_FIELD_PATTERN,
    COPYBOOK_OCCURS_PATTERN,
    COPYBOOK_PIC_PATTERN,
    COPYBOOK_USAGE_PATTERN,
)


class CopybookParser(BaseTextParser):
    RIGHT_SEQUENCE_PATTERN = re.compile(
        r"^(?P<body>.*?)(?:\s+(?P<right>\d{8}))\s*$",
        flags=re.IGNORECASE,
    )

    def __init__(self) -> None:
        self.diagnostics: list[str] = []

    def parse(
        self,
        text: str,
        source_label: str = "Copybook",
    ) -> list[CopybookField]:
        self.diagnostics = []
        if not str(text or "").strip():
            self.diagnostics.append(f"{source_label}: empty copybook text.")
            return []

        logical_lines = self._logical_lines(text)
        output: list[CopybookField] = []

        # ADDED: level-breakdown counters for a self-explanatory diagnostic.
        data_field_count = 0        # real data fields (levels 01-49, 66, 77)
        condition_name_count = 0    # 88-level condition names
        filler_count = 0            # skipped FILLER lines

        for line in logical_lines:
            match = COPYBOOK_FIELD_PATTERN.search(line)

            if not match:
                continue

            level = str(match.group("level") or "").strip()
            name = str(match.group("name") or "").strip().upper()
            rest = str(match.group("rest") or "")

            if not name:
                continue

            if name == "FILLER":
                filler_count += 1   # ADDED: track skipped FILLER
                continue

            # ADDED: classify by level for the breakdown diagnostic.
            if level == "88":
                condition_name_count += 1
            else:
                data_field_count += 1

            output.append(
                CopybookField(
                    level=level,
                    name=name,
                    picture=self._picture(rest),
                    usage=self._usage(rest),
                    occurs=self._occurs(rest),
                )
            )

        self.diagnostics.append(
            f"{source_label}: logical copybook lines parsed: {len(logical_lines)}"
        )

        # CHANGED: total count now annotated with the level breakdown so the
        # UI number ("Copybook Fields") is self-explanatory. The returned list
        # length is UNCHANGED, so the UI metric behaves exactly as before.
        self.diagnostics.append(
            f"{source_label}: copybook fields parsed: {len(output)} "
            f"(data fields: {data_field_count}, "
            f"88-condition names: {condition_name_count}, "
            f"FILLER skipped: {filler_count})"
        )

        return output

    def _picture(
        self,
        text: str,
    ) -> str:
        match = COPYBOOK_PIC_PATTERN.search(str(text or ""))

        if not match:
            return ""

        return str(match.group("pic") or "").strip().upper().rstrip(".")

    def _usage(
        self,
        text: str,
    ) -> str:
        match = COPYBOOK_USAGE_PATTERN.search(str(text or ""))

        if not match:
            return ""

        return str(match.group("usage") or "").strip().upper().rstrip(".")

    def _occurs(
        self,
        text: str,
    ) -> str:
        match = COPYBOOK_OCCURS_PATTERN.search(str(text or ""))

        if not match:
            return ""

        return str(match.group("occurs") or "").strip()

    def _logical_lines(
        self,
        text: str,
    ) -> list[str]:
        output: list[str] = []
        buffer = ""

        for raw_line in str(text or "").splitlines():
            line = self._copybook_body_line(raw_line)
            if not line.strip():
                continue

            if COPYBOOK_COMMENT_OR_SKIP_PATTERN.search(line):
                continue

            if line.lstrip().startswith("*") or line.lstrip().startswith("/"):
                continue

            if buffer:
                buffer = f"{buffer} {line.strip()}"
            else:
                buffer = line.strip()

            if "." in line:
                parts = buffer.split(".")

                for part in parts[:-1]:
                    clean = part.strip()
                    if clean:
                        output.append(clean + ".")

                buffer = parts[-1].strip()

        if buffer.strip():
            output.append(buffer.strip())

        return output

    def _copybook_body_line(
        self,
        raw_line: str,
    ) -> str:
        text = str(raw_line or "").rstrip("\n").rstrip("\r")

        if not text.strip():
            return ""

        if len(text) > 6 and text[:6].strip().isdigit():
            indicator = text[6:7]

            if indicator in ("*", "/"):
                return ""

            body = text[7:] if len(text) > 7 else ""
            return self._remove_right_sequence(body).strip()

        return self._remove_right_sequence(text).strip()

    def _remove_right_sequence(
        self,
        text: str,
    ) -> str:
        value = str(text or "").rstrip()

        match = self.RIGHT_SEQUENCE_PATTERN.match(value)
        if not match:
            return value

        body = str(match.group("body") or "").rstrip()
        right = str(match.group("right") or "")
        if not right:
            return value
        if not right.isdigit():
            return value
        return body


__all__ = [
    "CopybookParser",
]