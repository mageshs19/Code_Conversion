# LOCATION: src/idms_db2_phase2/testing/console/progress_bar.py
# ACTION: CREATE NEW FILE

"""Progress bar rendering and the indeterminate pulse animation.

The runners report no intermediate progress: each is a subprocess that
prints a summary when it finishes. A percentage would therefore be a
fiction, so a moving segment is used instead. It says "still working"
without claiming to know how far along it is.

The animation is skipped entirely when stdout is not a terminal, so a
piped transcript contains one static line per step rather than hundreds
of carriage returns.
"""

from __future__ import annotations

import sys
import threading

from idms_db2_phase2.testing.console.terminal import TerminalCapabilities
from rules.batch_console_rules import (
    BAR_CLOSE,
    BAR_OPEN,
    BAR_WIDTH,
    CARRIAGE_RETURN,
    CLEAR_PAD_WIDTH,
    ERASE_LINE,
    PULSE_INTERVAL_SECONDS,
    PULSE_SEGMENT,
)


class ProgressBar:
    """Draws the bar and owns the animation thread."""

    def __init__(self, capabilities: TerminalCapabilities) -> None:
        self.capabilities = capabilities
        self._stop: threading.Event | None = None
        self._thread: threading.Thread | None = None

    # =================================================================
    # Rendering
    # =================================================================
    def render(self, fraction: float = 1.0) -> str:
        filled = max(0, min(BAR_WIDTH, round(BAR_WIDTH * fraction)))
        return (
            BAR_OPEN
            + self.capabilities.filled * filled
            + self.capabilities.empty * (BAR_WIDTH - filled)
            + BAR_CLOSE
        )

    def _segment(self, position: int) -> str:
        cells = [self.capabilities.empty] * BAR_WIDTH
        for offset in range(PULSE_SEGMENT):
            cells[(position + offset) % BAR_WIDTH] = self.capabilities.filled
        return BAR_OPEN + "".join(cells) + BAR_CLOSE

    # =================================================================
    # Animation
    # =================================================================
    @property
    def running(self) -> bool:
        return self._thread is not None

    def start(self, prefix: str, suffix: str) -> None:
        """Begin the pulse. No-op when the console is not interactive."""
        if not self.capabilities.interactive:
            return

        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._pulse,
            args=(prefix, suffix, self._stop),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if self._stop is not None:
            self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._stop = None
        self._thread = None

    def _pulse(
        self,
        prefix: str,
        suffix: str,
        stop: threading.Event,
    ) -> None:
        position = 0
        while not stop.is_set():
            sys.stdout.write(
                f"{CARRIAGE_RETURN}{prefix}{self._segment(position)} {suffix}"
            )
            sys.stdout.flush()
            position = (position + 1) % BAR_WIDTH
            stop.wait(PULSE_INTERVAL_SECONDS)

    # =================================================================
    # Line control
    # =================================================================
    def clear_line(self) -> None:
        """Erase the animated line before writing the final one.

        Writing spaces and returning is not enough: the spaces persist in
        the terminal buffer and end up in any copied transcript, which is
        why the first version left a long tail of whitespace after every
        completed step.
        """
        if not self.capabilities.interactive:
            return

        if self.capabilities.ansi:
            sys.stdout.write(f"{CARRIAGE_RETURN}{ERASE_LINE}")
        else:
            sys.stdout.write(
                CARRIAGE_RETURN + " " * CLEAR_PAD_WIDTH + CARRIAGE_RETURN
            )

        sys.stdout.flush()