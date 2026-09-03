from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.field_reference_rewriter_patterns import (
    COBOL_IDENTIFIER_PATTERN,
    LEVEL_NUMBER_FIELD_PATTERN,
    REDEFINES_BASE_PATTERN,
    REDEFINES_FIELD_PATTERN,
)


class FieldReferenceFieldExtractor:
    """Pure text helpers for extracting COBOL field names and keys.

    This class does not access repositories or resolve DB2 metadata.
    Regex patterns live in patterns/field_reference_rewriter_patterns.py.
    """

    def extract_field_name(self, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""

        text = text.replace(".", " ")

        level_match = LEVEL_NUMBER_FIELD_PATTERN.match(text)
        if level_match:
            return level_match.group(2)

        redefines_match = REDEFINES_FIELD_PATTERN.match(text)
        if redefines_match:
            return redefines_match.group(1)

        tokens = COBOL_IDENTIFIER_PATTERN.findall(text)
        if not tokens:
            return ""

        return tokens[0]

    def extract_redefines_base(self, value: str) -> str:
        text = str(value or "")
        match = REDEFINES_BASE_PATTERN.search(text)
        if not match:
            return ""
        return match.group(1)

    def field_key(self, value: str) -> str:
        return NameNormalizer.to_cobol(value)

    def first_non_empty(self, *values: str) -> str:
        for value in values:
            text = str(value or "").strip()
            if text:
                return text
        return ""