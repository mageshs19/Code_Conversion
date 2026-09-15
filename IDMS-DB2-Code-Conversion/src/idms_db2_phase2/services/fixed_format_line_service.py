# LOCATION: src/idms_db2_phase2/services/fixed_format_line_service.py
# ACTION: REPLACE ENTIRE FILE

"""Fixed-format COBOL line helper service.

No regex.
No business hardcoding.

Purpose:
- Preserve existing left sequence, indicator, body, and right sequence layout.
- Allow services to update only the COBOL body area safely.

CORRECTION 1 - silent truncation
--------------------------------
build() previously did:

    safe_body = str(body or "")[: self.BODY_WIDTH].ljust(self.BODY_WIDTH)

which cut any body longer than columns 8-72 without telling anyone, so

    MOVE NR-IDGOOD-479EVEF OF DCLDZEVEFTV    TO WS-NR-ID-GOOD

was written out as

    MOVE NR-IDGOOD-479EVEF OF DCLDZEVEFTV    TO WS-NR-ID-GO

Truncation is never a correct outcome for COBOL source:
- build()                 raises BodyOverflowError instead of truncating.
- build_or_none()         returns None instead of raising.
- replace_body()          is total: returns the ORIGINAL line unchanged when
                          the new body does not fit.
- replace_body_wrapped()  returns one or more physical lines.

CORRECTION 2 - sequence numbers leaking into the body
-----------------------------------------------------
is_fixed_line() previously required a full 80 columns AND a numeric right
sequence:

    len(text) >= 80 and text[0:6].isdigit() and text[72:80].isdigit()

A hand-maintained member often carries a short line such as

    001690/

(7 characters, page eject, no right sequence). That failed the test, so
split() returned the WHOLE line as the body. The left sequence and the
indicator then became COBOL text, and a later terminator pass produced

    001690/.

which is not a valid COBOL statement.

A line is now fixed-format when columns 1-6 are numeric and column 7 holds
a valid indicator. The right sequence is optional. split() pads short lines
so column access is always safe.

CORRECTION 3 - partial sequence dropped
----------------------------------------
build() assembled 80 columns only when BOTH sequences were present. With the
relaxed parser a short line yields a left sequence and an empty right
sequence, so the left sequence was being discarded. build() now assembles
whenever EITHER sequence is present and pads the missing side.

CORRECTION 4 - two-line wrap ceiling
-------------------------------------
wrap_body() refused any statement needing more than two physical lines, so
long generated bodies were silently skipped. wrap_body_lines() wraps into N
lines. wrap_body() keeps its original two-line contract for existing callers.

Migration note: any caller that relied on build() truncating must switch to
replace_body_wrapped() or pre-check with body_fits().
"""

from __future__ import annotations


class BodyOverflowError(ValueError):
    """Raised when a COBOL body would not fit columns 8-72."""


class FixedFormatLineService:
    """Utility for fixed-format COBOL lines.

    Physical layout:
      - Columns 1-6  : left sequence
      - Column  7    : indicator
      - Columns 8-72 : COBOL body
      - Columns 73-80: right sequence
    """

    LEFT_SEQUENCE_START = 0
    LEFT_SEQUENCE_END = 6
    INDICATOR_INDEX = 6
    BODY_START = 7
    BODY_END = 72
    RIGHT_SEQUENCE_START = 72
    RIGHT_SEQUENCE_END = 80
    BODY_WIDTH = 65
    LEFT_SEQUENCE_WIDTH = 6
    RIGHT_SEQUENCE_WIDTH = 8

    # Shortest line on which columns 1-6 and column 7 can be read.
    MIN_ADDRESSABLE_LENGTH = 7

    COMMENT_INDICATORS = ("*", "/")
    DEBUG_INDICATORS = ("D", "d")
    CONTINUATION_INDICATOR = "-"
    BLANK_INDICATOR = " "

    # Every indicator the COBOL standard permits in column 7.
    VALID_INDICATORS = (" ", "*", "/", "D", "d", "-")

    # Extra indent applied to a continuation physical line when a statement
    # has to be wrapped. Relative to the first line's own indent.
    WRAP_CONTINUATION_INDENT = "  "

    # Upper bound on physical lines produced by one logical statement.
    # A statement needing more than this is almost certainly malformed.
    WRAP_MAX_LINES = 4

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    def is_fixed_line(self, line: str) -> bool:
        """True when columns 1-6 are numeric and column 7 is a valid indicator.

        The right sequence (73-80) is deliberately NOT required. Many
        hand-maintained members leave it blank or truncate the line, and
        demanding it caused the left sequence to be parsed as COBOL text.
        """
        text = str(line or "").rstrip("\n")

        if len(text) < self.MIN_ADDRESSABLE_LENGTH:
            return False

        if not text[
            self.LEFT_SEQUENCE_START : self.LEFT_SEQUENCE_END
        ].isdigit():
            return False

        return text[self.INDICATOR_INDEX] in self.VALID_INDICATORS

    def is_strict_fixed_line(self, line: str) -> bool:
        """The original, stricter test: full 80 columns, both sequences numeric.

        Kept for callers that specifically need a fully sequenced line,
        for example the final resequencer.
        """
        text = str(line or "").rstrip("\n")
        return (
            len(text) >= self.RIGHT_SEQUENCE_END
            and text[
                self.LEFT_SEQUENCE_START : self.LEFT_SEQUENCE_END
            ].isdigit()
            and text[
                self.RIGHT_SEQUENCE_START : self.RIGHT_SEQUENCE_END
            ].isdigit()
        )

    def split(self, line: str) -> tuple[str, str, str, str]:
        """Return (left_sequence, indicator, body, right_sequence).

        Short lines are padded to 80 columns first, so every slice is safe
        and a missing right sequence comes back as spaces rather than
        corrupting the body.
        """
        text = str(line or "").rstrip("\n")

        if self.is_fixed_line(text):
            padded = text.ljust(self.RIGHT_SEQUENCE_END)
            left = padded[self.LEFT_SEQUENCE_START : self.LEFT_SEQUENCE_END]
            indicator = padded[self.INDICATOR_INDEX]
            body = padded[self.BODY_START : self.BODY_END]
            right = padded[
                self.RIGHT_SEQUENCE_START : self.RIGHT_SEQUENCE_END
            ]
            return left, indicator, body, right

        return "", "", text, ""

    def body(self, line: str) -> str:
        return self.split(line)[2]

    def logical(self, line: str) -> str:
        return self.body(line).strip()

    def indicator(self, line: str) -> str:
        return self.split(line)[1]

    def left_sequence(self, line: str) -> str:
        return self.split(line)[0]

    def right_sequence(self, line: str) -> str:
        return self.split(line)[3]

    def leading_spaces(self, text: str, default: str = "") -> str:
        value = str(text or "")
        if not value:
            return default
        count = len(value) - len(value.lstrip(" "))
        return value[:count] if count > 0 else default

    def body_indent(self, line: str) -> str:
        return self.leading_spaces(self.body(line))

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------
    def is_comment_or_control_line(self, line: str) -> bool:
        """True for comment, page-eject and debug lines.

        These must never be re-indented, re-wrapped or terminated.
        """
        text = str(line or "").rstrip("\n")

        if not text.strip():
            return False

        if self.is_fixed_line(text):
            marker = text[self.INDICATOR_INDEX]
            return marker in self.COMMENT_INDICATORS + self.DEBUG_INDICATORS

        stripped = text.lstrip()
        return bool(stripped) and stripped[0] in self.COMMENT_INDICATORS

    def is_comment_line(self, line: str) -> bool:
        return self.indicator(line) in self.COMMENT_INDICATORS

    def is_debug_line(self, line: str) -> bool:
        return self.indicator(line) in self.DEBUG_INDICATORS

    def is_continuation_line(self, line: str) -> bool:
        return self.indicator(line) == self.CONTINUATION_INDICATOR

    def is_blank(self, line: str) -> bool:
        return not self.logical(line)

    def is_sequence_artifact(self, line: str) -> bool:
        """True when the BODY is nothing but a leaked source sequence number.

        Produced by the old parser, for example:

            002520     001690/.

        The body here is '001690/.' - six digits, an optional indicator
        character and an optional period. Such a line is not COBOL and must
        be dropped, never terminated or re-indented.

        No regex: plain character inspection only.
        """
        candidate = self.logical(line)

        if not candidate:
            return False

        if candidate.endswith("."):
            candidate = candidate[:-1]

        if candidate and candidate[-1] in self.COMMENT_INDICATORS:
            candidate = candidate[:-1]

        candidate = candidate.strip()

        return (
            len(candidate) == self.LEFT_SEQUENCE_WIDTH
            and candidate.isdigit()
        )

    # ------------------------------------------------------------------
    # Width
    # ------------------------------------------------------------------
    def body_fits(self, body: str) -> bool:
        return len(str(body or "").rstrip()) <= self.BODY_WIDTH

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------
    def build(
        self,
        left_sequence: str,
        indicator: str,
        body: str,
        right_sequence: str,
    ) -> str:
        """Assemble one 80-column line.

        Raises BodyOverflowError rather than truncating. Silent truncation
        destroys COBOL source; a caller must decide to skip or to wrap.

        The line is assembled whenever EITHER sequence is present. A missing
        side is padded, so a short source line keeps its left sequence
        instead of losing it. The final resequencer rewrites columns 1-6 and
        73-80 afterwards.
        """
        clean_body = str(body or "").rstrip()

        if not self.body_fits(clean_body):
            raise BodyOverflowError(
                f"COBOL body needs {len(clean_body)} columns, "
                f"only {self.BODY_WIDTH} are available: {clean_body!r}"
            )

        left = str(left_sequence or "")
        right = str(right_sequence or "")

        if not left and not right:
            return clean_body

        marker = str(indicator or "")[:1] or self.BLANK_INDICATOR
        if marker not in self.VALID_INDICATORS:
            marker = self.BLANK_INDICATOR

        padded_left = left.rjust(self.LEFT_SEQUENCE_WIDTH)[
            : self.LEFT_SEQUENCE_WIDTH
        ]
        padded_right = right.ljust(self.RIGHT_SEQUENCE_WIDTH)[
            : self.RIGHT_SEQUENCE_WIDTH
        ]
        padded_body = clean_body.ljust(self.BODY_WIDTH)

        return f"{padded_left}{marker}{padded_body}{padded_right}"

    def build_or_none(
        self,
        left_sequence: str,
        indicator: str,
        body: str,
        right_sequence: str,
    ) -> str | None:
        try:
            return self.build(left_sequence, indicator, body, right_sequence)
        except BodyOverflowError:
            return None

    def emit(
        self,
        left_sequence: str,
        indicator: str,
        body: str,
        right_sequence: str,
    ) -> list[str]:
        """Render a logical body as one or more physical lines.

        Never truncates and never refuses: the body is wrapped as many times
        as needed, up to WRAP_MAX_LINES.
        """
        clean_body = str(body or "").rstrip()

        if self.body_fits(clean_body):
            return [
                self.build(left_sequence, indicator, clean_body, right_sequence)
            ]

        indent = self.leading_spaces(clean_body, default="")
        bodies = self.wrap_body_lines(
            clean_body,
            continuation_indent=indent + self.WRAP_CONTINUATION_INDENT,
        )

        if not bodies:
            raise BodyOverflowError(
                f"COBOL body cannot be wrapped within "
                f"{self.WRAP_MAX_LINES} lines: {clean_body!r}"
            )

        return [
            self.build(left_sequence, indicator, part, right_sequence)
            for part in bodies
        ]

    # ------------------------------------------------------------------
    # Body replacement
    # ------------------------------------------------------------------
    def replace_body(self, line: str, new_body: str) -> str:
        """Replace the body, or return the line unchanged when it will not fit.

        Total function: never raises, never truncates. A rewrite that cannot
        be represented is simply not applied.
        """
        left, indicator, _old_body, right = self.split(line)
        rebuilt = self.build_or_none(left, indicator, new_body, right)
        return rebuilt if rebuilt is not None else str(line or "").rstrip("\n")

    def replace_body_strict(self, line: str, new_body: str) -> str:
        """Replace the body, raising BodyOverflowError when it will not fit."""
        left, indicator, _old_body, right = self.split(line)
        return self.build(left, indicator, new_body, right)

    def replace_body_wrapped(self, line: str, new_body: str) -> list[str]:
        """Replace the body, wrapping onto further physical lines if needed.

        Returns one line when the body fits, several lines when it has to be
        split at word boundaries, and the original single line when even a
        wrapped form cannot be represented.

        Callers must EXTEND their output list, not append.
        """
        original = str(line or "").rstrip("\n")
        left, indicator, old_body, right = self.split(original)
        clean_body = str(new_body or "").rstrip()

        if self.body_fits(clean_body):
            return [self.replace_body(original, clean_body)]

        if not self.is_fixed_line(original):
            return [clean_body]

        indent = self.leading_spaces(old_body, default="    ")
        bodies = self.wrap_body_lines(
            clean_body,
            continuation_indent=indent + self.WRAP_CONTINUATION_INDENT,
        )

        if not bodies:
            return [original]

        rendered: list[str] = []
        for part in bodies:
            built = self.build_or_none(left, indicator, part, right)
            if built is None:
                return [original]
            rendered.append(built)

        return rendered

    # ------------------------------------------------------------------
    # Wrapping
    # ------------------------------------------------------------------
    def wrap_body(
        self,
        body: str,
        continuation_indent: str,
    ) -> list[str]:
        """Split one logical body into at most TWO fixed-format bodies.

        Original contract preserved for existing callers. Returns an empty
        list when the statement cannot be represented in two lines. Use
        wrap_body_lines() when more than two lines are acceptable.
        """
        bodies = self.wrap_body_lines(
            body,
            continuation_indent=continuation_indent,
            max_lines=2,
        )
        return bodies if len(bodies) == 2 else []

    def wrap_body_lines(
        self,
        body: str,
        continuation_indent: str,
        max_lines: int | None = None,
    ) -> list[str]:
        """Split one logical body into N fixed-format bodies.

        Splits on word boundaries only, so a data-name is never cut in half.
        Returns an empty list when the statement still does not fit within
        max_lines, so the caller can skip the rewrite rather than emit
        corrupt source.
        """
        limit = max_lines if max_lines is not None else self.WRAP_MAX_LINES
        clean_body = str(body or "").rstrip()
        indent = self.leading_spaces(clean_body, default="")
        words = clean_body.split()

        if not words or limit < 1:
            return []

        first_limit = self.BODY_WIDTH - len(indent)
        next_limit = self.BODY_WIDTH - len(continuation_indent)

        if first_limit <= 0 or next_limit <= 0:
            return []

        # A single word longer than the window can never be wrapped.
        if any(len(word) > max(first_limit, next_limit) for word in words):
            return []

        bodies: list[str] = []
        remaining = list(words)
        is_first = True

        while remaining:
            if len(bodies) >= limit:
                return []

            prefix = indent if is_first else continuation_indent
            window = first_limit if is_first else next_limit

            taken: list[str] = []
            for word in remaining:
                candidate = " ".join(taken + [word])
                if len(candidate) <= window:
                    taken.append(word)
                    continue
                break

            if not taken:
                return []

            bodies.append(prefix + " ".join(taken))
            remaining = remaining[len(taken) :]
            is_first = False

        if len(bodies) < 2:
            return []

        return bodies