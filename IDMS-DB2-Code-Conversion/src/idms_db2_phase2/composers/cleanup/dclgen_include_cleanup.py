"""
DCLGEN include cleanup.

Ensures an EXEC SQL INCLUDE exists for every referenced DCLGEN group that
the DCLGEN repository knows about but that is not already included.
"""

from idms_db2_phase2.composers.cleanup.cleanup_message_collector import (
    CleanupMessageCollector,
)
from idms_db2_phase2.composers.cleanup.cobol_cleanup_line_utils import (
    CobolCleanupLineUtils,
)
from idms_db2_phase2.repositories.dclgen_repository import DclgenRepository
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.cobol_cleanup_patterns import (
    DCL_GROUP_PATTERN,
    EXEC_SQL_INCLUDE_PATTERN,
    LINKAGE_SECTION_PATTERN,
)


class DclgenIncludeCleanup:
    def __init__(
        self,
        dclgen_repository: DclgenRepository,
        messages: CleanupMessageCollector,
        line_utils: CobolCleanupLineUtils | None = None,
    ) -> None:
        self.dclgen_repository = dclgen_repository
        self.messages = messages
        self.line_utils = line_utils or CobolCleanupLineUtils()

    def _logical(self, line: str) -> str:
        return self.line_utils.logical(line)

    def apply(self, text: str) -> str:
        existing_includes = self._existing_includes(text)
        referenced_tables = self._referenced_dclgen_tables(text)

        missing_tables = [
            table
            for table in referenced_tables
            if table not in existing_includes
            and self.dclgen_repository.has_table(table)
        ]

        if not missing_tables:
            return text

        include_lines: list[str] = []

        for table in missing_tables:
            include_lines.extend(
                [
                    " EXEC SQL",
                    f"    INCLUDE {table}",
                    " END-EXEC.",
                ]
            )
            self.messages.add("added_dclgen_include", table=table)

        lines = text.splitlines()
        insert_index = self._db2_include_insert_index(lines)

        if insert_index < 0:
            return text.rstrip() + "\n" + "\n".join(include_lines) + "\n"

        updated = lines[:insert_index] + include_lines + lines[insert_index:]
        return "\n".join(updated).rstrip() + "\n"

    def _existing_includes(self, text: str) -> set[str]:
        output: set[str] = set()

        for match in EXEC_SQL_INCLUDE_PATTERN.finditer(text):
            include_name = NameNormalizer.normalize(match.group("include"))
            if include_name:
                output.add(include_name)

        return output

    def _referenced_dclgen_tables(self, text: str) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        for match in DCL_GROUP_PATTERN.finditer(text):
            table = NameNormalizer.normalize(match.group("table"))
            if not table:
                continue
            if table in seen:
                continue
            seen.add(table)
            output.append(table)

        return output

    def _db2_include_insert_index(self, lines: list[str]) -> int:
        last_include_end = -1
        in_exec_sql = False
        include_seen_in_block = False

        for index, line in enumerate(lines):
            logical = self._logical(line).upper()

            if logical.startswith("EXEC SQL"):
                in_exec_sql = True
                include_seen_in_block = False

            if in_exec_sql and "INCLUDE " in logical:
                include_seen_in_block = True

            if in_exec_sql and logical.startswith("END-EXEC"):
                if include_seen_in_block:
                    last_include_end = index + 1
                in_exec_sql = False
                include_seen_in_block = False

        if last_include_end >= 0:
            return last_include_end

        for index, line in enumerate(lines):
            if LINKAGE_SECTION_PATTERN.match(line):
                return index

        return -1