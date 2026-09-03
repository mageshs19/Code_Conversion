"""
Fixed-format COBOL line parser.

Responsibilities:
- Parse already sequenced 80-column COBOL lines.
- Parse unsequenced COBOL lines.
- Strip old left and right sequence numbers.
- Preserve COBOL body indentation.
- Detect indicator column values.

Important:
- A true left sequence number must start in column 1 and be exactly six
  digits.
- COBOL level numbers such as 01, 03, 05, 10, 20, 77, and 88 must never be
  treated as sequence numbers.
- Old right sequence numbers may appear separated by spaces or accidentally
  attached to the COBOL body. Both cases are handled conservatively.

Regex patterns live in patterns/fixed_format_patterns.py; layout constants and
statement starters live in rules/fixed_format_rules.py. Loose-sequence
stripping is provided by FixedFormatSequenceStripper.
"""

from __future__ import annotations

from idms_db2_phase2.composers.fixed_format_sequence_stripper import (
    FixedFormatSequenceStripper,
)
from patterns.fixed_format_patterns import (
    DEBUG_LINE_PATTERN,
    TRUE_LEFT_SEQUENCE_PATTERN,
)
from rules.fixed_format_rules import (
    BODY_WIDTH,
    COMMENT_INDICATOR,
    DEBUG_INDICATOR,
    PAGE_INDICATOR,
    SPACE_INDICATOR,
    TOTAL_WIDTH,
    VALID_INDICATORS,
)


class FixedFormatLineParser(FixedFormatSequenceStripper):
    """Parses fixed-format and loose COBOL lines safely."""

    def parse_line(self, line: str) -> dict[str, str | bool]:
        text = str(line or "").rstrip()

        fixed = self.parse_fixed_80_line(text)
        if fixed is not None:
            return fixed

        body = self.remove_loose_sequence_numbers(text)
        indicator = self.indicator_for_body(body)
        body = self.strip_inline_indicator(body=body, indicator=indicator)

        return {
            "left_sequence": "",
            "indicator": indicator,
            "body": body,
            "right_sequence": "",
            "is_fixed_format": False,
        }

    def parse_fixed_80_line(self, line: str) -> dict[str, str | bool] | None:
        text = str(line or "")
        if not self._is_fixed_format_line(text):
            return None

        indicator = text[6:7]
        if indicator not in VALID_INDICATORS:
            indicator = SPACE_INDICATOR

        return {
            "left_sequence": text[:6],
            "indicator": indicator,
            "body": text[7:72].rstrip(),
            "right_sequence": text[72:80],
            "is_fixed_format": True,
        }

    def body_for_boolean_merge(self, line: str) -> str:
        return str(self.parse_line(line).get("body", ""))

    def indicator_for_body(self, body: str) -> str:
        text = str(body or "")
        if not text:
            return SPACE_INDICATOR

        stripped = text.lstrip()
        if stripped.startswith(COMMENT_INDICATOR):
            return COMMENT_INDICATOR
        if stripped.startswith(PAGE_INDICATOR):
            return PAGE_INDICATOR
        if DEBUG_LINE_PATTERN.match(text):
            return DEBUG_INDICATOR
        return SPACE_INDICATOR

    def strip_inline_indicator(self, body: str, indicator: str) -> str:
        text = str(body or "")

        if indicator in {COMMENT_INDICATOR, PAGE_INDICATOR}:
            stripped = text.lstrip()
            if stripped.startswith(indicator):
                return stripped[1:].lstrip()

        if indicator == DEBUG_INDICATOR and DEBUG_LINE_PATTERN.match(text):
            stripped = text.lstrip()
            if stripped[:1].upper() == DEBUG_INDICATOR:
                return stripped[1:].lstrip()

        return text.rstrip()

    def replace_body_preserving_sequence(
        self, original_line: str, new_body: str
    ) -> str:
        text = str(original_line or "").rstrip()
        parsed = self.parse_line(text)

        if bool(parsed.get("is_fixed_format")):
            left = str(parsed.get("left_sequence") or "").zfill(6)[-6:]
            indicator = str(parsed.get("indicator") or SPACE_INDICATOR)[:1]
            right = str(parsed.get("right_sequence") or "").zfill(8)[-8:]
            if indicator not in VALID_INDICATORS:
                indicator = SPACE_INDICATOR
            body = str(new_body or "").rstrip()
            return f"{left}{indicator}{body[:BODY_WIDTH].ljust(BODY_WIDTH)}{right}"

        match = TRUE_LEFT_SEQUENCE_PATTERN.match(text)
        if match:
            left = str(match.group("left") or "").zfill(6)[-6:]
            return f"{left} {new_body}"

        return str(new_body or "").rstrip()

    def is_debug_line(self, stripped: str) -> bool:
        return bool(DEBUG_LINE_PATTERN.match(str(stripped or "")))

    def _is_fixed_format_line(self, line: str) -> bool:
        text = str(line or "")
        if len(text) < TOTAL_WIDTH:
            return False
        if not text[:6].isdigit():
            return False
        if not text[72:80].isdigit():
            return False
        return True