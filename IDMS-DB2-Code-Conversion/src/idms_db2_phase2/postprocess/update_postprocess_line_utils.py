from __future__ import annotations

import re

from patterns.update_restart_patterns import (
    COPY_INCLUDE_TOKEN_PATTERN_TEMPLATE,
    END_PROGRAM_PATTERN,
    LINKAGE_SECTION_PATTERN,
    PARAGRAPH_HEADER_PATTERN,
    PROCEDURE_DIVISION_PATTERN,
    WORKING_STORAGE_SECTION_PATTERN,
)


class UpdatePostprocessLineUtils:
    def lines(
        self,
        text: str,
    ) -> list[str]:
        return str(text or "").replace("\r\n", "\n").replace("\r", "\n").splitlines()

    def join(
        self,
        lines: list[str],
    ) -> str:
        return "\n".join(lines).rstrip() + "\n"

    def logical(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()

        if len(text) >= 72 and text[:6].strip().isdigit():
            return text[7:72].strip()

        if len(text) > 6 and text[:6].strip().isdigit():
            body = text[6:]

            if len(body) >= 8 and body[-8:].strip().isdigit():
                body = body[:-8]

            if body[:1] in ("*", "/", "D"):
                return body.strip()

            return body.strip()

        return text.strip()

    def logical_text(
        self,
        cobol_text: str,
    ) -> str:
        return "\n".join(
            self.logical(line)
            for line in self.lines(cobol_text)
        )

    def logical_contains(
        self,
        cobol_text: str,
        expected: str,
    ) -> bool:
        target = str(expected or "").strip().upper()

        if not target:
            return False

        for line in self.lines(cobol_text):
            logical = self.logical(line).upper()

            if target in logical:
                return True

        return False

    def contains_copy(
        self,
        cobol_text: str,
        include_name: str,
    ) -> bool:
        target = str(include_name or "").strip().upper()

        if not target:
            return False

        pattern = re.compile(
            COPY_INCLUDE_TOKEN_PATTERN_TEMPLATE.format(
                include_name=re.escape(target),
            ),
            flags=re.IGNORECASE,
        )

        return bool(pattern.search(self.logical_text(cobol_text)))

    def data_division_insert_line_index(
        self,
        lines: list[str],
    ) -> int:
        for index, line in enumerate(lines):
            logical = self.logical(line)

            if LINKAGE_SECTION_PATTERN.match(logical):
                return index

        for index, line in enumerate(lines):
            logical = self.logical(line)

            if PROCEDURE_DIVISION_PATTERN.match(logical):
                return index

        for index, line in enumerate(lines):
            logical = self.logical(line)

            if WORKING_STORAGE_SECTION_PATTERN.match(logical):
                return index + 1

        return -1

    def procedure_paragraph_insert_line_index(
        self,
        lines: list[str],
    ) -> int:
        for index, line in enumerate(lines):
            logical = self.logical(line)

            if END_PROGRAM_PATTERN.match(logical):
                return index

        for line in lines:
            logical = self.logical(line)

            if PROCEDURE_DIVISION_PATTERN.match(logical):
                return len(lines)

        return -1

    def find_paragraph_range(
        self,
        lines: list[str],
        paragraph_name: str,
    ) -> tuple[int, int] | None:
        target = str(paragraph_name or "").upper().rstrip(".")

        for index, line in enumerate(lines):
            logical = self.logical(line).upper().rstrip(".")

            if logical != target:
                continue

            end = index + 1

            while end < len(lines):
                next_logical = self.logical(lines[end]).strip()

                if end > index + 1 and PARAGRAPH_HEADER_PATTERN.match(next_logical):
                    break

                end += 1

            return index, end

        return None