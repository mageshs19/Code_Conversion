# LOCATION: src/idms_db2_phase2/testing/batch_console.py
# ACTION: REPLACE ENTIRE FILE

"""Console renderer for batch execution.

Layout only. Capability detection lives in console/terminal.py and the
animation in console/progress_bar.py, so this class decides WHAT a line
says and those two decide whether it can be drawn.

Design constraints
------------------
- Standard library only. The project's dependency list is deliberately
  short and a console renderer does not justify adding to it.
- Works in cmd.exe, PowerShell and a piped file. When stdout is not a
  terminal the animation is skipped, so a captured log holds one static
  line per step.
- Colour is an enhancement, never a requirement: every status is also
  spelled out as a word.

CORRECTIONS
-----------
1. verdict() embedded escape sequences directly inside f-string
   expressions. That is a syntax error before Python 3.12 and, more
   importantly, put a colour code in the layout layer where the palette
   belongs. It now uses the declared COLOUR_GREEN and COLOUR_RED.

2. step_finish() cleared the animated line by writing spaces and
   returning the cursor. The spaces survived in the terminal buffer and
   appeared as a long whitespace tail in any copied transcript.
   ProgressBar.clear_line() now erases the line properly.

3. closing() printed the Finished stamp immediately under the verdict.
   A blank line separates them.
"""

from __future__ import annotations

import sys
from datetime import datetime

from idms_db2_phase2.testing.console.progress_bar import ProgressBar
from idms_db2_phase2.testing.console.terminal import (
    Palette,
    TerminalCapabilities,
)
from rules.batch_console_rules import (
    COLOUR_GREEN,
    COLOUR_RED,
    COUNT_FILE_PLURAL,
    COUNT_FILE_SINGULAR,
    COUNT_NONE,
    FINISHED_TEMPLATE,
    INDENT,
    LABEL_WIDTH,
    RULE_HEAVY,
    RULE_LIGHT,
    STARTED_TEMPLATE,
    STATUS_COLOURS,
    STATUS_RUNNING,
    STATUS_WIDTH,
    STEP_COUNTER_TEMPLATE,
    STEP_LABEL_WIDTH,
    SUMMARY_COLUMN_SECONDS,
    SUMMARY_COLUMN_STATUS,
    SUMMARY_COLUMN_STEP,
    SUMMARY_HEADER_TEMPLATE,
    SUMMARY_ROW_TEMPLATE,
    SUMMARY_TOTAL_TEMPLATE,
    TIMESTAMP_FORMAT,
    TITLE,
    VALUE_UNKNOWN,
    VERDICT_FAILED_PLURAL,
    VERDICT_FAILED_SINGULAR,
    VERDICT_PASSED,
)

SUMMARY_STATUS_WIDTH = 12
SECONDS_TEMPLATE = "{seconds:>6.1f}s"


class BatchConsole:
    """Renders the batch execution report to stdout."""

    def __init__(self, quiet: bool = False) -> None:
        self.quiet = quiet
        self.capabilities = TerminalCapabilities()
        self.palette = Palette(self.capabilities)
        self.bar = ProgressBar(self.capabilities)

    @property
    def animated(self) -> bool:
        return self.capabilities.interactive and not self.quiet

    # =================================================================
    # Frame
    # =================================================================
    def banner(self) -> None:
        stamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        self._line(RULE_HEAVY)
        self._line(f"{INDENT}{self.palette.bold(TITLE)}")
        self._line(
            f"{INDENT}{self.palette.dim(STARTED_TEMPLATE.format(stamp=stamp))}"
        )
        self._line(RULE_HEAVY)
        self._line("")

    def closing(self) -> None:
        stamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        self._line("")
        self._line(
            f"{INDENT}{self.palette.dim(FINISHED_TEMPLATE.format(stamp=stamp))}"
        )
        self._line(RULE_HEAVY)

    def section(self, title: str) -> None:
        self._line(f"{INDENT}{self.palette.bold(title)}")
        self._line(f"{INDENT}{RULE_LIGHT}")

    def blank(self) -> None:
        self._line("")

    # =================================================================
    # Key / value
    # =================================================================
    def key_value(self, label: str, value: object) -> None:
        text = VALUE_UNKNOWN if value is None else str(value)
        self._line(f"{INDENT}{label:<{LABEL_WIDTH}}{text}")

    def file_count(self, label: str, count: int) -> None:
        if count <= 0:
            value = COUNT_NONE
        elif count == 1:
            value = COUNT_FILE_SINGULAR.format(count=count)
        else:
            value = COUNT_FILE_PLURAL.format(count=count)

        self.key_value(label, value)

    # =================================================================
    # Step progress
    # =================================================================
    def step_start(self, index: int, total: int, label: str) -> None:
        """Print the step line and begin the animation."""
        prefix = self._step_prefix(index, total, label)
        running = self._status(STATUS_RUNNING)

        if not self.animated:
            self._line(f"{prefix}{self.bar.render(0.0)} {running}")
            return

        self.bar.start(prefix, running)

    def step_finish(
        self,
        index: int,
        total: int,
        label: str,
        status: str,
        seconds: float,
        note: str = "",
    ) -> None:
        """Stop the animation and replace the line with the outcome."""
        self.bar.stop()

        prefix = self._step_prefix(index, total, label)
        suffix = SECONDS_TEMPLATE.format(seconds=seconds)
        if note:
            suffix = f"{suffix}  {self.palette.dim(note)}"

        if self.animated:
            self.bar.clear_line()

        self._line(
            f"{prefix}{self.bar.render(1.0)} {self._status(status)} {suffix}"
        )

    # =================================================================
    # Summary
    # =================================================================
    def summary_header(self) -> None:
        header = SUMMARY_HEADER_TEMPLATE.format(
            step=SUMMARY_COLUMN_STEP,
            status=SUMMARY_COLUMN_STATUS,
            seconds=SUMMARY_COLUMN_SECONDS,
        )
        self._line(INDENT + self.palette.dim(header))

    def summary_row(self, label: str, status: str, seconds: float) -> None:
        self._line(
            INDENT
            + SUMMARY_ROW_TEMPLATE.format(
                step=label,
                status=self._status(status, width=SUMMARY_STATUS_WIDTH),
                seconds=f"{seconds:.1f}",
            )
        )

    def summary_total(self, seconds: float, failures: int) -> None:
        self._line(f"{INDENT}{RULE_LIGHT}")
        self._line(
            INDENT
            + SUMMARY_TOTAL_TEMPLATE.format(
                seconds=seconds,
                failures=failures,
            )
        )

    def verdict(self, failures: int) -> None:
        self._line("")

        if failures == 0:
            self._line(
                f"{INDENT}{self.palette.paint(VERDICT_PASSED, COLOUR_GREEN)}"
            )
            return

        template = (
            VERDICT_FAILED_SINGULAR if failures == 1
            else VERDICT_FAILED_PLURAL
        )
        self._line(
            INDENT
            + self.palette.paint(
                template.format(count=failures),
                COLOUR_RED,
            )
        )

    def detail(self, title: str, body: str) -> None:
        if not str(body or "").strip():
            return

        self._line("")
        self._line(f"{INDENT}{self.palette.bold(title)}")
        self._line(f"{INDENT}{RULE_LIGHT}")

        for raw in body.strip().splitlines():
            self._line(f"{INDENT}{raw.rstrip()}")

    # =================================================================
    # Internals
    # =================================================================
    @staticmethod
    def _step_prefix(index: int, total: int, label: str) -> str:
        counter = STEP_COUNTER_TEMPLATE.format(index=index, total=total)
        return f"{INDENT}{counter} {label:<{STEP_LABEL_WIDTH}}"

    def _status(self, status: str, width: int = STATUS_WIDTH) -> str:
        """Pad BEFORE colouring, so escape codes never affect alignment."""
        return self.palette.paint(
            str(status).ljust(width),
            STATUS_COLOURS.get(status, ""),
        )

    @staticmethod
    def _line(text: str) -> None:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()