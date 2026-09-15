# LOCATION: src/idms_db2_phase2/ui/message_classifier.py
# ACTION: CREATE NEW FILE

"""Classifies pipeline messages into severity and category.

Pure logic: no Streamlit, no file access, no COBOL knowledge. The UI
layer renders whatever this returns.

Classification order
--------------------
1. PREFIX  - the text before the first colon. A source that only ever
             reports failures, or only ever reports normal work, is
             decided once here.
2. KEYWORD - applied only when the prefix does not decide.
3. DEFAULT - Info. Most of the list is pass narration, so an unmatched
             message is far more likely to be narration than a fault.

Deliberate default
------------------
Defaulting to Info rather than Warning is the whole point of this class.
The previous UI treated every message as a warning, which buried the two
that mattered under eighty that did not.
"""

from __future__ import annotations

from dataclasses import dataclass

from rules.validation_display_rules import (
    CATEGORY_SEPARATOR,
    ERROR_KEYWORDS,
    ERROR_PREFIXES,
    FALLBACK_CATEGORY,
    INFO_PREFIXES,
    MAX_CATEGORY_WORDS,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_ORDER,
    SEVERITY_WARNING,
    WARNING_KEYWORDS,
    WARNING_PREFIXES,
)


@dataclass(frozen=True)
class ClassifiedMessage:
    """One pipeline message with its severity and category."""

    text: str
    severity: str
    category: str

    @property
    def is_actionable(self) -> bool:
        return self.severity in (SEVERITY_ERROR, SEVERITY_WARNING)


class MessageClassifier:
    """Assigns a severity and a category to a pipeline message."""

    # =================================================================
    # Public entry points
    # =================================================================
    def classify(self, message: str) -> ClassifiedMessage:
        text = " ".join(str(message or "").split())

        if not text:
            return ClassifiedMessage("", SEVERITY_INFO, FALLBACK_CATEGORY)

        prefix = self._prefix(text)
        severity = self._severity_from_prefix(prefix)

        if severity is None:
            severity = self._severity_from_keywords(text)

        return ClassifiedMessage(
            text=text,
            severity=severity,
            category=self._category(prefix),
        )

    def classify_all(self, messages: list[str]) -> list[ClassifiedMessage]:
        """Classify a list, de-duplicated, severity-ordered."""
        seen: set[str] = set()
        out: list[ClassifiedMessage] = []

        for message in messages or []:
            item = self.classify(message)
            if not item.text or item.text in seen:
                continue
            seen.add(item.text)
            out.append(item)

        return self.sort(out)

    @staticmethod
    def sort(items: list[ClassifiedMessage]) -> list[ClassifiedMessage]:
        """Errors first, then warnings, then info. Stable within a band."""
        rank = {name: index for index, name in enumerate(SEVERITY_ORDER)}
        return sorted(
            items,
            key=lambda item: (rank.get(item.severity, len(rank)), item.category),
        )

    @staticmethod
    def counts(items: list[ClassifiedMessage]) -> dict[str, int]:
        result = {name: 0 for name in SEVERITY_ORDER}
        for item in items:
            if item.severity in result:
                result[item.severity] += 1
        return result

    @staticmethod
    def categories(items: list[ClassifiedMessage]) -> list[str]:
        return sorted({item.category for item in items if item.category})

    @staticmethod
    def of_severity(
        items: list[ClassifiedMessage],
        severity: str,
    ) -> list[ClassifiedMessage]:
        return [item for item in items if item.severity == severity]

    # =================================================================
    # Internals
    # =================================================================
    @staticmethod
    def _prefix(text: str) -> str:
        """Text before the first colon, when it reads like a source name.

        A long run of words before the colon is prose, not a prefix, so
        it is rejected rather than becoming a category of one.
        """
        if CATEGORY_SEPARATOR not in text:
            return ""

        candidate = text.split(CATEGORY_SEPARATOR, 1)[0].strip()
        if not candidate or len(candidate.split()) > MAX_CATEGORY_WORDS:
            return ""

        return candidate

    @staticmethod
    def _severity_from_prefix(prefix: str) -> str | None:
        if not prefix:
            return None

        lowered = prefix.lower()

        if lowered.startswith(ERROR_PREFIXES):
            return SEVERITY_ERROR

        if lowered.startswith(WARNING_PREFIXES):
            return SEVERITY_WARNING

        if lowered.startswith(INFO_PREFIXES):
            return SEVERITY_INFO

        return None

    @staticmethod
    def _severity_from_keywords(text: str) -> str:
        lowered = text.lower()

        if any(keyword in lowered for keyword in ERROR_KEYWORDS):
            return SEVERITY_ERROR

        if any(keyword in lowered for keyword in WARNING_KEYWORDS):
            return SEVERITY_WARNING

        return SEVERITY_INFO

    @staticmethod
    def _category(prefix: str) -> str:
        if not prefix:
            return FALLBACK_CATEGORY
        return prefix[:1].upper() + prefix[1:]