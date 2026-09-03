from __future__ import annotations

from typing import Optional

from idms_db2_phase2.postprocess.update_metadata_models import (
    CobolFileInfo,
    norm_name,
    upper,
)

from patterns.dynamic_metadata_patterns import (
    COPY_RE,
    EOF_IF_RE,
    EOF_MOVE_RE,
    EOF_UNTIL_RE,
    FD_LINE_RE,
    FD_RECORD_01_RE,
    FIELD_USE_RE,
    MOVE_FIELD_RE,
    PROGRAM_RE,
    READ_LINE_RE,
    READ_RE,
    RECORD_CONTAINS_RE,
    SECTION_END_RE,
    SELECT_LINE_RE,
    SELECT_RE,
)


class UpdateCobolFileResolver:
    def resolve_program_id(
        self,
        *,
        generated_cobol: str,
        source_cobol: str,
        target_program_id: str,
    ) -> str:
        for text in [generated_cobol, source_cobol]:
            logical_text = self.logical_statement_text(text)
            match = PROGRAM_RE.search(logical_text)

            if match:
                return upper(match.group(1))

        return upper(target_program_id)

    def parse_cobol_files(
        self,
        *,
        source_cobol: str,
        generated_cobol: str,
    ) -> dict[str, CobolFileInfo]:
        files: dict[str, CobolFileInfo] = {}

        for raw_text in [source_cobol, generated_cobol]:
            self._parse_from_logical_text(
                files=files,
                raw_text=raw_text,
            )
            self._parse_from_physical_lines(
                files=files,
                raw_text=raw_text,
            )

        return files

    def choose_input_file(
        self,
        files: dict[str, CobolFileInfo],
    ) -> CobolFileInfo:
        read_files = [item for item in files.values() if item.read_target]
        if read_files:
            return read_files[0]

        fd_files = [item for item in files.values() if item.fd_record]
        if fd_files:
            return fd_files[0]

        return next(iter(files.values()))

    def extract_copy_statements(
        self,
        text: str,
    ) -> set[str]:
        logical_text = self.logical_statement_text(text)

        return {
            norm_name(match.group(1))
            for match in COPY_RE.finditer(logical_text)
        }

    def extract_source_field_references(
        self,
        source_cobol: str,
    ) -> set[str]:
        refs: set[str] = set()
        logical_text = self.logical_statement_text(source_cobol)

        for match in FIELD_USE_RE.finditer(logical_text):
            refs.add(norm_name(match.group(1)))

        for match in MOVE_FIELD_RE.finditer(logical_text):
            refs.add(norm_name(match.group(1)))

        return refs

    def resolve_legacy_eof_switch(
        self,
        *,
        source_cobol: str,
        generated_cobol: str,
    ) -> str:
        combined = "\n".join(
            [
                self.logical_statement_text(source_cobol),
                self.logical_statement_text(generated_cobol),
            ]
        )

        candidates: dict[str, int] = {}

        for pattern in [EOF_UNTIL_RE, EOF_IF_RE, EOF_MOVE_RE]:
            for match in pattern.finditer(combined):
                name = norm_name(match.group(1))

                if not name:
                    continue

                if "EOF" not in name:
                    continue

                candidates[name] = candidates.get(name, 0) + 1

        if not candidates:
            return ""

        return sorted(
            candidates.items(),
            key=lambda item: item[1],
            reverse=True,
        )[0][0]

    def _parse_from_logical_text(
        self,
        *,
        files: dict[str, CobolFileInfo],
        raw_text: str,
    ) -> None:
        text = self.logical_statement_text(raw_text)

        for match in SELECT_RE.finditer(text):
            name = upper(match.group(1))
            assignment = upper(match.group(2))
            files.setdefault(name, CobolFileInfo(name=name)).assignment = assignment

        for match in READ_RE.finditer(text):
            file_name = upper(match.group(1))
            read_target = upper(match.group(2))

            if read_target:
                files.setdefault(
                    file_name,
                    CobolFileInfo(name=file_name),
                ).read_target = read_target

    def _parse_from_physical_lines(
        self,
        *,
        files: dict[str, CobolFileInfo],
        raw_text: str,
    ) -> None:
        current_fd = ""

        for raw_line in str(raw_text or "").splitlines():
            line = self.fixed_format_body_line(raw_line).strip()

            if not line:
                continue

            select_match = SELECT_LINE_RE.search(line)

            if select_match:
                file_name = upper(select_match.group(1))
                assignment = upper(select_match.group(2))
                files.setdefault(
                    file_name,
                    CobolFileInfo(name=file_name),
                ).assignment = assignment
                continue

            fd_match = FD_LINE_RE.search(line)

            if fd_match:
                current_fd = upper(fd_match.group(1))
                files.setdefault(current_fd, CobolFileInfo(name=current_fd))
                continue

            if current_fd:
                length_match = RECORD_CONTAINS_RE.search(line)

                if length_match:
                    files[current_fd].record_length = int(length_match.group(1))
                    continue

                record_match = FD_RECORD_01_RE.search(line)

                if record_match:
                    files[current_fd].fd_record = upper(record_match.group(1))
                    continue

                if SECTION_END_RE.search(line):
                    current_fd = ""

            read_match = READ_LINE_RE.search(line)

            if read_match:
                file_name = upper(read_match.group(1))
                read_target = upper(read_match.group(2))

                if read_target:
                    files.setdefault(
                        file_name,
                        CobolFileInfo(name=file_name),
                    ).read_target = read_target

    def fixed_format_body_text(
        self,
        text: str,
    ) -> str:
        output: list[str] = []

        for raw_line in str(text or "").splitlines():
            body = self.fixed_format_body_line(raw_line)

            if not body:
                continue

            if body.lstrip().startswith("*") or body.lstrip().startswith("/"):
                continue

            output.append(body)

        return "\n".join(output)

    def fixed_format_body_line(
        self,
        line: str,
    ) -> str:
        text = str(line or "").rstrip()

        if not text.strip():
            return ""

        if len(text) >= 72 and text[:6].strip().isdigit():
            indicator = text[6:7]

            if indicator in ("*", "/"):
                return ""

            return text[7:72].strip()

        if len(text) > 6 and text[:6].strip().isdigit():
            body = text[6:]

            if len(body) >= 8 and body[-8:].strip().isdigit():
                body = body[:-8]

            if body[:1] in ("*", "/", "D"):
                return body.strip()

            return body.strip()

        return text.strip()

    def logical_statement_text(
        self,
        text: str,
    ) -> str:
        body_text = self.fixed_format_body_text(text)
        statements: list[str] = []
        buffer = ""

        for raw_line in body_text.splitlines():
            line = raw_line.strip()

            if not line:
                continue

            if buffer:
                buffer = f"{buffer} {line}"
            else:
                buffer = line

            if "." in line:
                parts = buffer.split(".")

                for part in parts[:-1]:
                    clean = part.strip()

                    if clean:
                        statements.append(clean + ".")

                buffer = parts[-1].strip()

        if buffer:
            statements.append(buffer)

        return "\n".join(statements)