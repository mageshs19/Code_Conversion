from __future__ import annotations

import re

from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.field_reference_rewriter_patterns import (
    OF_IN_AFTER_PATTERN,
    OF_IN_BEFORE_PATTERN,
    QUALIFIED_REFERENCE_PATTERN,
)
from rules.field_reference_rewriter_rules import PROTECTED_BARE_PREFIXES


class FieldReferenceReplacementEngine:
    """
    Rewrites qualified and bare IDMS field references using resolved
    Sheet Mapping + DCLGEN host-reference maps.
    """

    def __init__(
        self,
        *,
        record_field_map: dict[str, dict[str, str]],
        rewrite_messages: list[str],
    ) -> None:
        self.record_field_map = record_field_map
        self.rewrite_messages = rewrite_messages

    def rewrite_qualified_references(
        self,
        text: str,
    ) -> str:
        def repl(match):
            source_field = NameNormalizer.to_cobol(match.group("field"))
            source_record = NameNormalizer.normalize(match.group("record"))

            target = self.target_for_record_field(
                record_name=source_record,
                source_field=source_field,
            )

            if not target:
                return match.group(0)

            self.rewrite_messages.append(
                f"Qualified field rewrite: {source_field} OF "
                f"{NameNormalizer.to_cobol(source_record)} -> {target}"
            )

            return target

        return QUALIFIED_REFERENCE_PATTERN.sub(
            repl,
            text,
        )

    def rewrite_bare_references(
        self,
        *,
        text: str,
        active_record: str,
    ) -> str:
        record = NameNormalizer.normalize(active_record)

        if not record:
            return text

        field_map = self.record_field_map.get(record, {})

        if not field_map:
            return text

        updated = str(text or "")

        for source_key, target_reference in sorted(
            field_map.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            source_name = NameNormalizer.to_cobol(source_key)

            if not source_name or not target_reference:
                continue

            if self.is_protected_bare_source_name(source_name):
                continue

            updated = self.replace_bare_identifier(
                text=updated,
                source_name=source_name,
                target_name=target_reference,
            )

        return updated

    def replace_bare_identifier(
        self,
        *,
        text: str,
        source_name: str,
        target_name: str,
    ) -> str:
        source = NameNormalizer.to_cobol(source_name)
        target = str(target_name or "").strip()

        if not source or not target:
            return text

        pattern = re.compile(
            rf"(?<![A-Z0-9-]){re.escape(source)}(?![A-Z0-9-])",
            flags=re.IGNORECASE,
        )

        def repl(match):
            before_text = text[: match.start()]
            after_text = text[match.end() :]

            if self.is_part_of_qualified_reference(
                before_text=before_text,
                after_text=after_text,
            ):
                return match.group(0)

            self.rewrite_messages.append(
                f"Bare field rewrite: {source} -> {target}"
            )

            return target

        return pattern.sub(
            repl,
            text,
        )

    def target_for_record_field(
        self,
        *,
        record_name: str,
        source_field: str,
    ) -> str:
        record = NameNormalizer.normalize(record_name)
        field = self.field_key(source_field)

        if not record or not field:
            return ""

        return self.record_field_map.get(record, {}).get(field, "")

    def field_key(
        self,
        value: str,
    ) -> str:
        return NameNormalizer.to_cobol(value)

    def is_protected_bare_source_name(
        self,
        source_name: str,
    ) -> bool:
        source = NameNormalizer.to_cobol(source_name).upper()

        if not source:
            return True

        for prefix in PROTECTED_BARE_PREFIXES:
            if source.startswith(prefix):
                return True

        return False

    def is_part_of_qualified_reference(
        self,
        *,
        before_text: str,
        after_text: str,
    ) -> bool:
        before = str(before_text or "").upper()
        after = str(after_text or "").upper()

        if OF_IN_BEFORE_PATTERN.search(before):
            return True

        if OF_IN_AFTER_PATTERN.match(after):
            return True

        return False


__all__ = [
    "FieldReferenceReplacementEngine",
]