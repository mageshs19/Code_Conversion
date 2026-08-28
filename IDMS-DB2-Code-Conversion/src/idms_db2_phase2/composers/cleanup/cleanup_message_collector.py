"""
Cleanup message collector.

A tiny shared container that accumulates COBOL cleanup messages. Sharing one
collector across all cleanup passes preserves the composer contract, where
conversion_service reads composer.messages after compose().
"""

from rules.cobol_cleanup_rules import CLEANUP_MESSAGES


class CleanupMessageCollector:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def reset(self) -> None:
        self.messages = []

    def add(self, key: str, **fields: str) -> None:
        template = CLEANUP_MESSAGES[key]
        self.messages.append(template.format(**fields))