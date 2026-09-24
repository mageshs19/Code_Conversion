# LOCATION: src/idms_db2_phase2/services/name_normalizer.py
# ACTION: REPLACE ENTIRE FILE

"""Generic name normalization helper.

This service contains name transformation logic only.
Regex patterns are stored in patterns/naming_patterns.py.

DEFECT FIX
----------
`normalize()` produces a DB2 identifier (hyphen -> underscore). It was
being used to render IDMS SET and RECORD names into generated COBOL
comments, which emitted

    *DB2: Converted OBTAIN FIRST VMBFAS WITHIN AR_VMBFRM1.

instead of the IDMS spelling `AR-VMBFRM1`. An IDMS set name is never a
DB2 identifier, so it must never pass through `normalize()` on its way
to output.

`to_idms_name()` is the explicit, self-documenting entry point for that
case. It is a thin alias of `to_cobol()` so the two can never drift.
"""

from patterns.naming_patterns import (
    FOUR_DIGIT_RECORD_SUFFIX_PATTERN,
    MULTIPLE_UNDERSCORE_PATTERN,
    NON_COMPACT_NAME_CHARACTER_PATTERN,
    NON_DB2_NAME_CHARACTER_PATTERN,
)


class NameNormalizer:

    @staticmethod
    def normalize(
        value: str | None,
    ) -> str:
        """Canonical DB2 identifier: upper case, underscore separated."""
        if value is None:
            return ""

        text = str(value).strip().upper()

        if not text:
            return ""

        text = text.replace("-", "_")
        text = text.replace(" ", "_")
        text = NON_DB2_NAME_CHARACTER_PATTERN.sub("_", text)
        text = MULTIPLE_UNDERSCORE_PATTERN.sub("_", text)

        return text.strip("_")

    @staticmethod
    def to_cobol(
        value: str | None,
    ) -> str:
        """Canonical COBOL identifier: upper case, hyphen separated."""
        return NameNormalizer.normalize(value).replace("_", "-")

    @staticmethod
    def to_idms_name(
        value: str | None,
    ) -> str:
        """IDMS SET / RECORD / AREA name as it must appear in output.

        Use this for anything that is written back into generated COBOL
        text as an IDMS name (comments, diagnostics, DB2-KEEP markers).
        Never use `normalize()` for that purpose: it emits a DB2
        identifier and corrupts the IDMS spelling.
        """
        return NameNormalizer.to_cobol(value)

    @staticmethod
    def compact(
        value: str | None,
    ) -> str:
        text = NameNormalizer.normalize(value)
        return NON_COMPACT_NAME_CHARACTER_PATTERN.sub("", text)

    @staticmethod
    def remove_record_suffix(
        value: str | None,
    ) -> str:
        text = NameNormalizer.normalize(value)

        if not text:
            return ""

        return FOUR_DIGIT_RECORD_SUFFIX_PATTERN.sub("", text)


__all__ = ["NameNormalizer"]