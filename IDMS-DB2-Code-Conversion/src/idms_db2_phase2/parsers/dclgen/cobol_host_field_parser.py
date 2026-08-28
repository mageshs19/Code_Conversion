# LOCATION: src/idms_db2_phase2/parsers/dclgen/cobol_host_field_parser.py
# ACTION: CREATE NEW FILE

"""Parses COBOL host fields (PIC / USAGE) from DCLGEN text."""

from __future__ import annotations

from patterns.dclgen_patterns import (
    COBOL_FIELD_PATTERN,
    COBOL_GROUP_PATTERN,
    DCLGEN_PIC_PATTERN,
    DCLGEN_USAGE_PATTERN,
)


class CobolHostFieldParser:
    def __init__(self, diagnostics: list[str]) -> None:
        self.diagnostics = diagnostics

    def parse(
        self,
        text: str,
        source_label: str,
    ) -> list[dict[str, str]]:
        fields: list[dict[str, str]] = []
        current_group = ""
        seen_group = False

        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            group_match = COBOL_GROUP_PATTERN.match(line)

            if group_match:
                current_group = group_match.group(1).upper()
                seen_group = True
                continue

            if not seen_group:
                continue

            match = COBOL_FIELD_PATTERN.match(line)
            if not match:
                continue

            level = match.group(1)
            name = match.group(2).upper()
            body = match.group("body") or ""
            nullable = name.upper().endswith("-NULL")

            pic = self._picture(body)
            usage = self._usage(body)

            if not pic and not usage:
                continue

            fields.append(
                {
                    "group": current_group,
                    "level": level,
                    "name": name,
                    "picture": pic,
                    "usage": usage,
                    "nullable_indicator": "Y" if nullable else "N",
                }
            )

        self.diagnostics.append(
            f"{source_label}: COBOL host field scan found "
            f"{len(fields)} field(s)."
        )
        return fields

    def _picture(self, text: str) -> str:
        match = DCLGEN_PIC_PATTERN.search(str(text or ""))
        if not match:
            return ""
        return match.group("pic").strip().upper()

    def _usage(self, text: str) -> str:
        match = DCLGEN_USAGE_PATTERN.search(str(text or ""))
        if not match:
            return ""
        return match.group(1).strip().upper()