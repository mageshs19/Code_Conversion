# LOCATION: src/idms_db2_phase2/parsers/dclgen/sql_name_normalizer.py
# ACTION: CREATE NEW FILE

"""DCLGEN SQL / COBOL name normalization helpers."""

from __future__ import annotations

from patterns.dclgen_patterns import (
    MULTIPLE_UNDERSCORE_PATTERN,
    SQL_NAME_CLEANUP_PATTERN,
)


class DclgenNameNormalizer:
    def normalize_sql_name(self, value: str) -> str:
        text = str(value or "").strip()
        text = text.strip('"').strip("'")
        text = text.strip(">").strip("[").strip("]")

        if "." in text:
            text = text.split(".")[-1]

        text = text.replace("-", "_")
        text = SQL_NAME_CLEANUP_PATTERN.sub("_", text.upper())
        text = MULTIPLE_UNDERSCORE_PATTERN.sub("_", text)

        return text.strip("_")

    def normalize_cobol_name_to_db2(self, value: str) -> str:
        text = str(value or "").strip().upper()
        text = text.replace("-", "_")
        text = SQL_NAME_CLEANUP_PATTERN.sub("_", text)
        text = MULTIPLE_UNDERSCORE_PATTERN.sub("_", text)

        return text.strip("_")

    def normalize_compare_name(self, value: str) -> str:
        text = self.normalize_cobol_name_to_db2(value)

        if text.startswith("DCL_"):
            return text[4:]

        if text.startswith("DCL"):
            return text[3:]

        return text