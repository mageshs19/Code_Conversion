# LOCATION: src/idms_db2_phase2/generators/db2_infrastructure/cobol_line_utils.py
# ACTION: CREATE NEW FILE

"""Stateless COBOL line helpers for DB2 infrastructure generation."""

from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer


class CobolLineUtils:
    def logical_line(self, line: str) -> str:
        text = str(line or "").rstrip()

        if len(text) >= 80:
            left = text[:6]
            body = text[7:72]
            if left.strip().isdigit():
                return body.strip()

        if len(text) > 6 and text[:6].strip().isdigit():
            return text[6:].strip()

        return text.strip()

    def comment_block(self, title: str) -> list[str]:
        return [f"* {title:<62}*"]

    def comma_lines(self, items: list[str], indent: str) -> list[str]:
        clean_items = [
            str(item or "").strip()
            for item in items
            if str(item or "").strip()
        ]
        output: list[str] = []
        for index, item in enumerate(clean_items):
            if index == 0:
                output.append(f"{indent}{item}")
            else:
                output.append(f"{indent}, {item}")
        return output

    def and_lines(self, items: list[str], indent: str) -> list[str]:
        clean_items = [
            str(item or "").strip()
            for item in items
            if str(item or "").strip()
        ]
        output: list[str] = []
        for index, item in enumerate(clean_items):
            prefix = "AND " if index > 0 else ""
            output.append(f"{indent}{prefix}{item}")
        return output

    def normalize_include_name(self, value: str) -> str:
        return NameNormalizer.normalize(value)