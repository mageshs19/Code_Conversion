# LOCATION: src/idms_db2_phase2/parsers/lrf_parser.py
# ACTION: CREATE NEW FILE
"""Parses IDMS subschema source into LogicalRecord metadata.

Reads only the LRF portion of the subschema:
    ADD LOGICAL RECORD ... ELEMENTS ARE ... COMMENTS ...
    ADD PATH-GROUP <verb> <lr> ... SELECT FOR KEYWORD ...

Area, record and set sections are recorded as context only.
No COBOL knowledge, no SQL, no Streamlit.
"""

from __future__ import annotations

from idms_db2_phase2.domain.models import (
    LogicalRecord,
    LrfPath,
    LrfPathCommand,
)
from patterns.lrf_patterns import (
    COMMENTS_PATTERN,
    ELEMENTS_ARE_PATTERN,
    ELEMENT_NAME_PATTERN,
    ERASE_PATTERN,
    FIND_OBTAIN_PATTERN,
    IF_SET_EMPTY_PATTERN,
    LOGICAL_RECORD_PATTERN,
    ON_STATUS_PATTERN,
    PATH_GROUP_PATTERN,
    QUOTED_TEXT_PATTERN,
    SELECT_KEYWORD_PATTERN,
    SUBSCHEMA_HEADER_PATTERN,
    WHERE_PATTERN,
)
from rules.lrf_rules import (
    DIAG_LRF_PATHS_TEMPLATE,
    DIAG_LRF_TOTAL_RECORDS_TEMPLATE,
)

COMMENT_PREFIXES = ("*", "-")


class LrfParser:
    def __init__(self) -> None:
        self.diagnostics: list[str] = []

    # ---- public API -------------------------------------------------
    def parse(self, text: str, source_label: str = "") -> list[LogicalRecord]:
        self.diagnostics = []
        records: dict[str, LogicalRecord] = {}

        subschema_name = ""
        schema_name = ""
        mode = ""                       # ELEMENTS | COMMENTS | PATH
        current_lr: LogicalRecord | None = None
        current_group_verb = ""
        current_path: LrfPath | None = None
        current_command: LrfPathCommand | None = None

        for number, raw_line in enumerate(str(text or "").splitlines(), start=1):
            line = raw_line.rstrip()
            stripped = line.strip()

            if not stripped or stripped.startswith("*"):
                continue

            header = SUBSCHEMA_HEADER_PATTERN.match(line)
            if header:
                subschema_name = header.group("subschema").upper()
                schema_name = header.group("schema").upper()
                continue

            # ---- ADD LOGICAL RECORD
            lr_match = LOGICAL_RECORD_PATTERN.match(line)
            if lr_match:
                name = lr_match.group("lr").upper()
                current_lr = records.setdefault(
                    name,
                    LogicalRecord(
                        logical_record_name=name,
                        subschema_name=subschema_name,
                        schema_name=schema_name,
                    ),
                )
                mode = ""
                current_path = None
                current_command = None
                continue

            if ELEMENTS_ARE_PATTERN.match(line):
                mode = "ELEMENTS"
                continue

            if COMMENTS_PATTERN.match(line):
                mode = "COMMENTS"
                continue

            # ---- ADD PATH-GROUP <verb> <lr>
            group = PATH_GROUP_PATTERN.match(line)
            if group:
                name = group.group("lr").upper()
                current_lr = records.setdefault(
                    name,
                    LogicalRecord(
                        logical_record_name=name,
                        subschema_name=subschema_name,
                        schema_name=schema_name,
                    ),
                )
                current_group_verb = group.group("verb").upper()
                mode = "PATH"
                current_path = None
                current_command = None
                continue

            # ---- SELECT FOR KEYWORD <keyword>
            keyword = SELECT_KEYWORD_PATTERN.match(line)
            if keyword and current_lr is not None:
                current_path = LrfPath(
                    keyword=keyword.group("keyword").upper(),
                    path_group_verb=current_group_verb,
                    logical_record=current_lr.logical_record_name,
                )
                current_lr.paths.append(current_path)
                current_command = None
                continue

            if stripped == ".":
                mode = ""
                current_path = None
                current_command = None
                continue

            # ---- body lines
            if mode == "ELEMENTS" and current_lr is not None:
                element = ELEMENT_NAME_PATTERN.match(stripped)
                if element:
                    value = element.group("record").upper()
                    if value not in current_lr.element_records:
                        current_lr.element_records.append(value)
                continue

            if mode == "COMMENTS" and current_lr is not None:
                for quoted in QUOTED_TEXT_PATTERN.finditer(stripped):
                    current_lr.comments.append(quoted.group("text"))
                continue

            if mode == "PATH" and current_path is not None:
                current_command = self._path_line(
                    stripped=stripped,
                    raw_line=raw_line,
                    number=number,
                    path=current_path,
                    current_command=current_command,
                )

        result = list(records.values())
        self.diagnostics.append(
            DIAG_LRF_TOTAL_RECORDS_TEMPLATE.format(count=len(result))
        )
        for record in result:
            self.diagnostics.append(
                DIAG_LRF_PATHS_TEMPLATE.format(
                    lr=record.logical_record_name,
                    count=len(record.paths),
                )
            )
        return result

    # ---- helpers ----------------------------------------------------
    def _path_line(
        self,
        *,
        stripped: str,
        raw_line: str,
        number: int,
        path: LrfPath,
        current_command: LrfPathCommand | None,
    ) -> LrfPathCommand | None:
        status = ON_STATUS_PATTERN.match(stripped)
        if status and current_command is not None:
            current_command.status_actions[status.group("status")] = (
                status.group("action").strip().upper()
            )
            return current_command

        where = WHERE_PATTERN.match(stripped)
        if where and current_command is not None:
            current_command.where_clause = where.group("clause").strip().upper()
            return current_command

        empty = IF_SET_EMPTY_PATTERN.match(stripped)
        if empty:
            command = LrfPathCommand(
                verb="IF",
                scope="NOT EMPTY" if empty.group("negate") else "EMPTY",
                within_name=empty.group("set_name").upper(),
                line_number=number,
                raw_line=raw_line,
            )
            path.commands.append(command)
            return command

        erase = ERASE_PATTERN.match(stripped)
        if erase:
            command = LrfPathCommand(
                verb="ERASE",
                record_name=erase.group("record").upper(),
                line_number=number,
                raw_line=raw_line,
            )
            path.commands.append(command)
            return command

        access = FIND_OBTAIN_PATTERN.match(stripped)
        if access:
            command = LrfPathCommand(
                verb=access.group("verb").upper(),
                scope=(access.group("scope") or "").upper(),
                record_name=access.group("record").upper(),
                within_name=(access.group("within") or "").upper(),
                line_number=number,
                raw_line=raw_line,
            )
            path.commands.append(command)
            return command

        return current_command