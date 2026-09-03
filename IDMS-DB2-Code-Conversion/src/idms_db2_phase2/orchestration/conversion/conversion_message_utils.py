from __future__ import annotations


class ConversionMessageUtils:
    """Message collection helpers shared by the conversion pipeline."""

    def _component_messages(self, component: object) -> list[str]:
        """Return messages from components that optionally expose them.

        Some transformers/composers expose a ``messages`` attribute; others do
        not. This keeps orchestration generic without forcing all components
        to implement the same diagnostics interface.
        """
        messages = getattr(component, "messages", [])
        if callable(messages):
            messages = messages()
        if not messages:
            return []
        return [
            str(message)
            for message in messages
            if str(message or "").strip()
        ]

    def _unique_messages(self, messages: list[str]) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()
        for message in messages:
            clean_message = str(message or "").strip()
            if not clean_message or clean_message in seen:
                continue
            seen.add(clean_message)
            output.append(clean_message)
        return output