# LOCATION: src/idms_db2_phase2/generators/db2_infrastructure/block_inserter.py
# ACTION: CREATE NEW FILE

"""Inserts the generated block into DATA DIVISION and adds DCLGEN INITIALIZE."""

from __future__ import annotations

import re

from idms_db2_phase2.generators.db2_infrastructure.infrastructure_patterns import (
    DATA_DIVISION_PATTERN,
    LINKAGE_SECTION_PATTERN,
    PROCEDURE_DIVISION_PATTERN,
    WORKING_STORAGE_PATTERN,
)
from idms_db2_phase2.services.name_normalizer import NameNormalizer


class BlockInserter:
    def __init__(self, line_utils) -> None:
        self.line_utils = line_utils

    def insert_in_data_division(self, text: str, block: str) -> str:
        for pattern in [LINKAGE_SECTION_PATTERN, PROCEDURE_DIVISION_PATTERN]:
            match = pattern.search(text)
            if match:
                return (
                    text[: match.start()].rstrip()
                    + "\n\n"
                    + block.rstrip()
                    + "\n\n"
                    + text[match.start():].lstrip()
                ).rstrip() + "\n"

        working_storage_match = WORKING_STORAGE_PATTERN.search(text)
        if working_storage_match:
            return (
                text[: working_storage_match.end()].rstrip()
                + "\n\n"
                + block.rstrip()
                + "\n\n"
                + text[working_storage_match.end():].lstrip()
            ).rstrip() + "\n"

        data_division_match = DATA_DIVISION_PATTERN.search(text)
        if data_division_match:
            return (
                text[: data_division_match.end()].rstrip()
                + "\n\n"
                + "WORKING-STORAGE SECTION."
                + "\n\n"
                + block.rstrip()
                + "\n\n"
                + text[data_division_match.end():].lstrip()
            ).rstrip() + "\n"

        return block.rstrip() + "\n\n" + text.rstrip() + "\n"

    def ensure_dclgen_initialization(
        self,
        text: str,
        include_names: list[str],
    ) -> str:
        clean_include_names = [
            self.line_utils.normalize_include_name(include_name)
            for include_name in include_names
            if self.line_utils.normalize_include_name(include_name)
        ]
        if not clean_include_names:
            return text

        missing_initializes = []
        for include_name in clean_include_names:
            group_name = "DCL" + NameNormalizer.to_cobol(include_name)
            if re.search(
                rf"\bINITIALIZE\s+{re.escape(group_name)}\b",
                text,
                flags=re.IGNORECASE,
            ):
                continue
            missing_initializes.append(group_name)

        if not missing_initializes:
            return text

        initialize_lines = [
            "* DB2: Initialize generated DCLGEN host groups."
        ]
        for group_name in missing_initializes:
            initialize_lines.append(f"INITIALIZE {group_name}.")

        block = "\n".join(initialize_lines)
        return self._insert_after_procedure_division(text=text, block=block)

    def _insert_after_procedure_division(self, text: str, block: str) -> str:
        lines = str(text or "").splitlines()
        output: list[str] = []
        inserted = False

        for line in lines:
            output.append(line)
            if inserted:
                continue
            logical = self.line_utils.logical_line(line)
            if PROCEDURE_DIVISION_PATTERN.match(logical):
                output.append(block)
                inserted = True

        if inserted:
            return "\n".join(output).rstrip() + "\n"

        return str(text or "").rstrip() + "\n\n" + block + "\n"