"""
Record-level Option B composer (IDMS-source-seeded, column-confirmed).

A record is UNMAPPED when ColumnNameResolver.columns_for_record(record)
returns an empty list. Covers the case where a Sheet Mapping ROW/table
exists (e.g. FFRECAB -> DZ01RSTB) but has zero usable columns.

For an unmapped record every referencing line is commented (record-level):
  - lines qualified with 'OF/IN <record>', AND
  - bare lines that move into a field of the record's naming family
    (the '-FF' family for FFRECAB, e.g. NS-SET-FF, NS-REC-FF-IN, NR-KY-FF).

Production comment layout (each emitted line is exactly 80 columns):
  - columns 1-6  : left sequence number (preserved from original line)
  - column 7     : '*' comment indicator
  - columns 8-72 : COBOL body (original indentation preserved)
  - columns 73-80: right sequence number (preserved from original line)

If a comment body does not fit in columns 8-72 it is wrapped onto the next
comment line (standard COBOL comment continuation), each still 80 columns.
"""

from __future__ import annotations

import re

from idms_db2_phase2.resolvers.column_name_resolver import ColumnNameResolver
from idms_db2_phase2.resolvers.table_name_resolver import TableNameResolver
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.idms_patterns import (
    ERASE_PATTERN,
    MODIFY_PATTERN,
    OBTAIN_CALC_PATTERN,
    OBTAIN_CALC_REVERSED_PATTERN,
    STORE_PATTERN,
)

BODY_WIDTH = 65          # columns 8-72
LEFT_WIDTH = 6           # columns 1-6
RIGHT_WIDTH = 8          # columns 73-80


class UnmappedRecordBlockComposer:

    OF_RECORD_PATTERN = re.compile(
        r"\b(?:OF|IN)\s+(?P<record>[A-Z][A-Z0-9-]*)\b",
        flags=re.IGNORECASE,
    )
    STATEMENT_END = re.compile(r"\.\s*$")
    LEFT_SEQ = re.compile(r"^(?P<left>\d{6})")
    RIGHT_SEQ = re.compile(r"(?P<seq>\d{8})\s*$")

    # FFRECAB restart-record field family: every FFRECAB field ends in
    # '-FF' or '-FF-<suffix>'. A plain counter like CTR-REC does NOT match.
    FF_FIELD_PATTERN = re.compile(
        r"\bTO\s+[A-Z0-9-]*-FF(?:-[A-Z0-9-]+)?\b",
        flags=re.IGNORECASE,
    )

    def __init__(
        self,
        table_name_resolver: TableNameResolver,
        column_name_resolver: ColumnNameResolver,
        original_idms_text: str = "",
    ) -> None:
        self.table_name_resolver = table_name_resolver
        self.column_name_resolver = column_name_resolver
        self.original_idms_text = original_idms_text or ""
        self.messages: list[str] = []

    def compose(self, text: str) -> str:
        if not text:
            return ""

        unmapped = self._discover_unmapped_records()
        if not unmapped:
            return text

        lines = text.replace("\r\n", "\n").split("\n")
        record_alt = "|".join(re.escape(r) for r in sorted(unmapped))
        record_ref = re.compile(
            r"\b(?:OF|IN)\s+(?:" + record_alt + r")\b",
            flags=re.IGNORECASE,
        )
        ff_family_active = "FFRECAB" in unmapped

        output: list[str] = []
        marked: set[str] = set()
        commented_any = False
        i = 0
        n = len(lines)

        while i < n:
            logical = self._logical(lines[i])

            if not logical or logical.startswith("*"):
                output.append(lines[i])
                i += 1
                continue

            # Full statement span (this line until a period line).
            span_end = i
            while span_end < n:
                span_logical = self._logical(lines[span_end])
                if self.STATEMENT_END.search(span_logical):
                    break
                span_end += 1
            span = list(range(i, min(span_end + 1, n)))
            span_logicals = [self._logical(lines[j]) for j in span]

            references_record = any(
                record_ref.search(l) for l in span_logicals
            )
            references_ff_field = ff_family_active and any(
                self.FF_FIELD_PATTERN.search(l) for l in span_logicals
            )
            touches_dcl = any("DCL" in l.upper() for l in span_logicals)

            if (references_record or references_ff_field) and not touches_dcl:
                record = self._record_of(span_logicals, unmapped)
                if not record and references_ff_field:
                    record = "FFRECAB"

                if record and record not in marked:
                    cobol_record = NameNormalizer.to_cobol(
                        NameNormalizer.normalize(record)
                    )
                    first_left, first_right = self._sequences(lines[span[0]])
                    output.extend(
                        self._comment_marker(
                            cobol_record, first_left, first_right
                        )
                    )
                    marked.add(record)

                for j in span:
                    output.extend(self._comment_line(lines[j]))

                commented_any = True
                i = span[-1] + 1
                continue

            output.append(lines[i])
            i += 1

        if commented_any:
            for record in sorted(marked):
                self.messages.append(
                    "Unmapped record block: commented all lines for "
                    f"{record} (record-level Option B)."
                )

        return "\n".join(output).rstrip() + "\n"

    # ---- discovery from ORIGINAL IDMS source ---------------------------

    def _discover_unmapped_records(self) -> set[str]:
        found: set[str] = set()
        text = self.original_idms_text
        if not text:
            return found

        patterns = (
            OBTAIN_CALC_PATTERN,
            OBTAIN_CALC_REVERSED_PATTERN,
            STORE_PATTERN,
            MODIFY_PATTERN,
            ERASE_PATTERN,
        )

        for raw in text.replace("\r\n", "\n").split("\n"):
            logical = self._logical(raw)
            upper = logical.upper()
            if not upper or upper.startswith("*"):
                continue
            for pattern in patterns:
                match = pattern.search(upper)
                if not match:
                    continue
                if "record" not in match.groupdict():
                    continue
                token = match.group("record")
                if not token:
                    continue
                normalized = NameNormalizer.normalize(token)
                if not normalized:
                    continue
                columns = self.column_name_resolver.columns_for_record(
                    normalized
                )
                if columns:
                    continue
                found.add(normalized.upper())

        return found

    # ---- helpers -------------------------------------------------------

    def _record_of(
        self,
        span_logicals: list[str],
        unmapped: set[str],
    ) -> str:
        for logical in span_logicals:
            for match in self.OF_RECORD_PATTERN.finditer(logical):
                token = NameNormalizer.normalize(
                    match.group("record")
                ).upper()
                if token in unmapped:
                    return token
        return ""

    def _sequences(self, line: str) -> tuple[str, str]:
        """Return (left6, right8) sequence numbers from a line, padded."""
        raw = str(line or "").rstrip("\n")
        left_match = self.LEFT_SEQ.match(raw)
        left = left_match.group("left") if left_match else "000000"
        right_match = self.RIGHT_SEQ.search(raw)
        right = right_match.group("seq") if right_match else "00000000"
        return left, right

    def _original_body(self, line: str) -> str:
        """Return columns 8-72 body of the original fixed-format line."""
        raw = str(line or "").rstrip("\n")
        text = re.sub(r"\s*\d{8}\s*$", "", raw)   # drop right seq
        if len(text) >= 8:
            return text[7:72].rstrip()
        # Unsequenced line: drop a leading 6-digit left seq if present.
        if len(text) >= 6 and text[:6].isdigit():
            return text[6:].rstrip()
        return text.rstrip()

    def _build_comment_lines(
        self,
        body: str,
        left: str,
        right: str,
    ) -> list[str]:
        """
        Build one or more 80-column comment lines for a body, wrapping at
        the 65-char body window (cols 8-72). Continuation lines repeat the
        '*' indicator and keep the same left/right sequence numbers.
        """
        clean = body.rstrip()
        if not clean:
            clean = ""

        chunks: list[str] = []
        if len(clean) <= BODY_WIDTH:
            chunks.append(clean)
        else:
            # Preserve leading indentation on the first chunk; wrap the
            # remainder with a continuation indent so it stays readable.
            indent_len = len(clean) - len(clean.lstrip(" "))
            indent = " " * min(indent_len, 8)
            remaining = clean
            first = True
            while remaining:
                if first:
                    piece = remaining[:BODY_WIDTH]
                    remaining = remaining[BODY_WIDTH:]
                    first = False
                else:
                    room = BODY_WIDTH - len(indent)
                    piece = indent + remaining[:room]
                    remaining = remaining[room:]
                chunks.append(piece)

        out: list[str] = []
        left6 = (left or "000000")[:LEFT_WIDTH].zfill(LEFT_WIDTH)
        right8 = (right or "00000000")[:RIGHT_WIDTH].zfill(RIGHT_WIDTH)
        for chunk in chunks:
            body_area = chunk[:BODY_WIDTH].ljust(BODY_WIDTH)
            out.append(f"{left6}*{body_area}{right8}")
        return out

    def _comment_line(self, line: str) -> list[str]:
        left, right = self._sequences(line)
        body = self._original_body(line)
        return self._build_comment_lines(body, left, right)

    def _comment_marker(
        self,
        cobol_record: str,
        left: str,
        right: str,
    ) -> list[str]:
        body = f" {cobol_record} - no DB2 columns, map manually."
        return self._build_comment_lines(body, left, right)

    @staticmethod
    def _logical(line: str) -> str:
        text = str(line or "")
        text = re.sub(r"^\s*\d{6}\s?", "", text)
        text = re.sub(r"\s*\d{8}\s*$", "", text)
        return text.strip()