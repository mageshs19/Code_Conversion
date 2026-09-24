# LOCATION: patterns/cursor_loop_patterns.py
# ACTION: CREATE NEW FILE
"""Regex for COBOL driving-loop idioms around a generated cursor.

Regex only. No rules, no constants, no names.
patterns/cursor_flow_patterns.py owns the ORIGINAL inline idiom and is
left untouched so the proven path cannot regress.
"""

from __future__ import annotations

import re

_NAME = r"[A-Z0-9][A-Z0-9-]*"

# PERFORM <para> THRU <para> UNTIL <condition>.     (all on one line)
PERFORM_SPAN_WITH_UNTIL_PATTERN = re.compile(
    rf"^PERFORM\s+(?P<paragraph>{_NAME})\s+(?:THRU|THROUGH)\s+"
    rf"(?P<through>{_NAME})\s+UNTIL\s+(?P<condition>.+?)\s*\.?\s*$",
    flags=re.IGNORECASE,
)

# PERFORM <para> THRU <para>                        (UNTIL on a later line)
PERFORM_SPAN_PATTERN = re.compile(
    rf"^PERFORM\s+(?P<paragraph>{_NAME})\s+(?:THRU|THROUGH)\s+"
    rf"(?P<through>{_NAME})\s*\.?\s*$",
    flags=re.IGNORECASE,
)

# PERFORM <para> UNTIL <condition>.                 (inline, one line)
PERFORM_INLINE_WITH_UNTIL_PATTERN = re.compile(
    rf"^PERFORM\s+(?P<paragraph>{_NAME})\s+UNTIL\s+"
    rf"(?P<condition>.+?)\s*\.?\s*$",
    flags=re.IGNORECASE,
)

# PERFORM <para>.                                   (UNTIL on a later line)
PERFORM_SIMPLE_PATTERN = re.compile(
    rf"^PERFORM\s+(?P<paragraph>{_NAME})\s*\.?\s*$",
    flags=re.IGNORECASE,
)

# UNTIL <condition>.                                (continuation line)
UNTIL_LINE_PATTERN = re.compile(
    r"^UNTIL\s+(?P<condition>.+?)\s*(?P<terminator>\.?)\s*$",
    flags=re.IGNORECASE,
)

# PERFORM nnn-OPEN|FETCH|CLOSE-<cursor>.
PERFORM_CURSOR_PARAGRAPH_PATTERN = re.compile(
    rf"^PERFORM\s+(?P<number>\d{{3,6}})-"
    rf"(?P<operation>OPEN|FETCH|CLOSE)-"
    rf"(?P<cursor>{_NAME})\s*\.?\s*$",
    flags=re.IGNORECASE,
)

# A cursor end-of-cursor condition name.
EOC_CONDITION_PATTERN = re.compile(
    rf"^{_NAME}-EOC$",
    flags=re.IGNORECASE,
)

# Paragraph / section headers, used to bound a scan.
PARAGRAPH_HEADER_PATTERN = re.compile(
    rf"^(?P<name>{_NAME})\s*\.\s*$",
    flags=re.IGNORECASE,
)

DIVISION_OR_SECTION_PATTERN = re.compile(
    r"^[A-Z0-9-]+\s+(DIVISION|SECTION)\b",
    flags=re.IGNORECASE,
)