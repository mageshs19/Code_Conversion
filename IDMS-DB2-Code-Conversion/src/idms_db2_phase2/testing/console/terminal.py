# LOCATION: src/idms_db2_phase2/testing/console/terminal.py
# ACTION: CREATE NEW FILE

"""Terminal capability detection and colour.

Answers three questions once, at startup, so no renderer has to guess:

  - is stdout a terminal, or is the batch being piped to a file?
  - can escape sequences be used?
  - can the console encode block glyphs, or must the bar be ASCII?

Colour is always an enhancement, never a requirement. Every status the
batch prints is also spelled out as a word, so a transcript with the
escapes stripped remains complete.
"""

from __future__ import annotations

import os
import sys

from rules.batch_console_rules import (
    BAR_EMPTY_ASCII,
    BAR_EMPTY_UNICODE,
    BAR_FILLED_ASCII,
    BAR_FILLED_UNICODE,
    COLOUR_BOLD,
    COLOUR_DIM,
    COLOUR_RESET,
    ENABLE_COLOUR,
    NO_COLOUR_ENV,
)

WINDOWS_STDOUT_HANDLE = -11
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 7


class TerminalCapabilities:
    """What this console can actually do."""

    def __init__(self) -> None:
        self._enable_windows_ansi()
        self.interactive = self._detect_interactive()
        self.colour = self._detect_colour()
        self.filled, self.empty = self._detect_glyphs()

    @property
    def ansi(self) -> bool:
        """True when escape sequences can be emitted.

        Tied to interactivity rather than to colour, because the
        erase-line sequence is still wanted when NO_COLOR is set.
        """
        return self.interactive

    # =================================================================
    # Detection
    # =================================================================
    @staticmethod
    def _detect_interactive() -> bool:
        try:
            return bool(sys.stdout.isatty())
        except Exception:  # noqa: BLE001
            return False

    def _detect_colour(self) -> bool:
        if not ENABLE_COLOUR:
            return False
        if os.environ.get(NO_COLOUR_ENV):
            return False
        return self.interactive

    @staticmethod
    def _detect_glyphs() -> tuple[str, str]:
        """Block glyphs when the console can encode them, else ASCII.

        A legacy Windows code page raises UnicodeEncodeError on the block
        characters, which would abort the batch over a cosmetic choice.
        """
        encoding = getattr(sys.stdout, "encoding", "") or ""
        try:
            BAR_FILLED_UNICODE.encode(encoding)
            return BAR_FILLED_UNICODE, BAR_EMPTY_UNICODE
        except (LookupError, UnicodeEncodeError, AttributeError):
            return BAR_FILLED_ASCII, BAR_EMPTY_ASCII

    @staticmethod
    def _enable_windows_ansi() -> None:
        """Turn on virtual terminal processing on legacy Windows consoles."""
        if os.name != "nt":
            return
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(
                kernel32.GetStdHandle(WINDOWS_STDOUT_HANDLE),
                ENABLE_VIRTUAL_TERMINAL_PROCESSING,
            )
        except Exception:  # noqa: BLE001
            pass


class Palette:
    """Applies colour, or does nothing when colour is unavailable."""

    def __init__(self, capabilities: TerminalCapabilities) -> None:
        self.capabilities = capabilities

    def paint(self, text: str, code: str) -> str:
        if not self.capabilities.colour or not code:
            return str(text)
        return f"{code}{text}{COLOUR_RESET}"

    def bold(self, text: str) -> str:
        return self.paint(text, COLOUR_BOLD)

    def dim(self, text: str) -> str:
        return self.paint(text, COLOUR_DIM)