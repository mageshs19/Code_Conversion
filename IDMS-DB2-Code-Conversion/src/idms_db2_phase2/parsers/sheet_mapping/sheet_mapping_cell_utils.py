from __future__ import annotations

from patterns.sheet_mapping_patterns import (
    CELL_WHITESPACE_PATTERN,
    HEADER_NON_ALPHANUMERIC_PATTERN,
    HEADER_WHITESPACE_PATTERN,
)


class SheetMappingCellUtils:
    """Cell and header text normalization helpers.

    Owns no schema and no regex definitions (patterns live in
    patterns/sheet_mapping_patterns.py).
    """

    def _cell_to_string(self, value) -> str:
        if value is None:
            return ""
        text = str(value)
        text = text.replace("\ufeff", "")
        text = text.replace("\xa0", " ")
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")
        text = CELL_WHITESPACE_PATTERN.sub(" ", text)
        return text.strip()

    def _normalize_header(self, value: str) -> str:
        text = self._cell_to_string(value)
        text = text.upper()
        text = text.replace("_", " ")
        text = HEADER_NON_ALPHANUMERIC_PATTERN.sub("", text)
        text = HEADER_WHITESPACE_PATTERN.sub(" ", text)
        return text.strip()