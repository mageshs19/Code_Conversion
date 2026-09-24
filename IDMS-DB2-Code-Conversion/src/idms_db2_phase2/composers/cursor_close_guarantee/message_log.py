# LOCATION: src/idms_db2_phase2/composers/cursor_close_guarantee/message_log.py
# ACTION: CREATE NEW FILE

"""Shared diagnostic collector for the cursor close-guarantee pass.

Every helper writes into ONE log instance so the composer can expose a
single `messages` list to conversion_service without each helper owning
its own list and drifting out of order.

Templates live in rules/cursor_close_guarantee_rules.py. This class never
formats a message it does not find there, so an unknown key is silently
ignored rather than raising in the middle of a conversion run.
"""

from __future__ import annotations

from rules.cursor_close_guarantee_rules import (
    CURSOR_CLOSE_GUARANTEE_MESSAGES,
)


class MessageLog:
    """Ordered diagnostic messages for one conversion run."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def reset(self) -> None:
        self.messages = []

    def log(self, key: str, **values) -> None:
        template = CURSOR_CLOSE_GUARANTEE_MESSAGES.get(key, "")

        if not template:
            return

        try:
            self.messages.append(template.format(**values))
        except (KeyError, IndexError):
            # A template/caller mismatch must never abort a conversion.
            self.messages.append(template)


__all__ = ["MessageLog"]