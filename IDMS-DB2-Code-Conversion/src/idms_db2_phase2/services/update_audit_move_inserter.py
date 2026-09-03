from __future__ import annotations

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from idms_db2_phase2.services.update_cobol_final_cleanup_utils import (
    UpdateCobolFinalCleanupUtils,
)
from patterns.update_final_feedback_patterns import (
    EXEC_SQL_END_PATTERN,
    EXEC_SQL_START_PATTERN,
    MOVE_TO_DCL_OF_REFERENCE_PATTERN,
    SET_KEYWORD_PATTERN,
    SQL_SET_ASSIGNMENT_PATTERN,
    UPDATE_STATEMENT_PATTERN,
    WHERE_KEYWORD_PATTERN,
)
from rules.timestamp_audit_rules import UPDATE_AUDIT_COLUMN_PREFIXES
from rules.update_cobol_final_cleanup_rules import (
    AUDIT_SOURCE_BY_KIND,
    TIMESTAMP_AUDIT_PREFIXES,
    UPDATE_FINAL_LOOKBACK_DUPLICATE_LIMIT,
    USER_AUDIT_PREFIXES,
)


class UpdateAuditMoveInserter:
    """
    Inserts audit MOVE statements before UPDATE SQL blocks.

    Only inserts moves for audit host variables already present in generated
    UPDATE SET assignments.
    """

    def __init__(
        self,
        *,
        fixed_format: FixedFormatLineService,
        utils: UpdateCobolFinalCleanupUtils,
    ) -> None:
        self.fixed_format = fixed_format
        self.utils = utils

    def insert_update_audit_moves(
        self,
        text: str,
    ) -> str:
        lines = text.splitlines()
        update_blocks = self.find_update_exec_sql_blocks(lines)

        if not update_blocks:
            return text.rstrip() + "\n"

        output = list(lines)

        for start, end in sorted(update_blocks, reverse=True):
            block = output[start : end + 1]
            audit_targets = self.audit_targets_from_update_block(block)

            if not audit_targets:
                continue

            reference_line = output[start]
            insert_lines: list[str] = []

            for group, host, audit_kind in audit_targets:
                if self.has_recent_move_to_host(
                    lines=output,
                    insert_index=start,
                    group=group,
                    host=host,
                ):
                    continue

                source = self.source_for_audit_kind(audit_kind)

                if not source:
                    continue

                move_logical = f"MOVE {source} TO {host} OF {group}"
                insert_lines.append(
                    self.fixed_format.replace_body(
                        reference_line,
                        self.utils.body_with_existing_indent(
                            original_line=reference_line,
                            new_logical=move_logical,
                        ),
                    )
                )

            if not insert_lines:
                continue

            output[start:start] = insert_lines

        return "\n".join(output).rstrip() + "\n"

    def find_update_exec_sql_blocks(
        self,
        lines: list[str],
    ) -> list[tuple[int, int]]:
        blocks: list[tuple[int, int]] = []
        in_exec_sql = False
        start = -1
        has_update = False

        for index, line in enumerate(lines):
            logical = self.fixed_format.logical(line)
            upper = logical.upper()

            if EXEC_SQL_START_PATTERN.match(logical):
                # One-line "EXEC SQL ... END-EXEC." (e.g. INCLUDE) must not
                # wedge the in_exec_sql flag open. If END-EXEC is on the same
                # line, this block opens and closes immediately and carries
                # no UPDATE, so skip it without entering multi-line mode.
                if "END-EXEC" in upper:
                    in_exec_sql = False
                    start = -1
                    has_update = False
                    continue
                in_exec_sql = True
                start = index
                has_update = False
                continue

            if in_exec_sql and UPDATE_STATEMENT_PATTERN.match(logical):
                has_update = True

            if in_exec_sql and EXEC_SQL_END_PATTERN.match(logical):
                if has_update:
                    blocks.append((start, index))
                in_exec_sql = False
                start = -1
                has_update = False

        return blocks
    
    def audit_targets_from_update_block(
        self,
        block: list[str],
    ) -> list[tuple[str, str, str]]:
        in_set = False
        targets: list[tuple[str, str, str]] = []

        for line in block:
            logical = self.fixed_format.logical(line)

            if SET_KEYWORD_PATTERN.match(logical):
                in_set = True
                continue

            if in_set and WHERE_KEYWORD_PATTERN.match(logical):
                break

            if not in_set:
                continue

            match = SQL_SET_ASSIGNMENT_PATTERN.match(logical.strip())

            if not match:
                continue

            column = str(match.group("column") or "").upper()
            group = str(match.group("group") or "").upper()
            host = str(match.group("host") or "").upper()

            audit_kind = self.audit_kind_for_column(column)

            if not audit_kind:
                continue

            targets.append((group, host, audit_kind))

        return self.unique_targets(targets)

    def audit_kind_for_column(
        self,
        column: str,
    ) -> str:
        normalized = str(column or "").upper()

        if not self.has_update_audit_prefix(normalized):
            return ""

        if normalized.startswith(TIMESTAMP_AUDIT_PREFIXES):
            return "timestamp"

        if normalized.startswith(USER_AUDIT_PREFIXES):
            return "user"

        return ""

    def has_update_audit_prefix(
        self,
        column: str,
    ) -> bool:
        normalized = str(column or "").upper()

        return any(
            normalized.startswith(str(prefix or "").upper())
            for prefix in UPDATE_AUDIT_COLUMN_PREFIXES
        )

    def source_for_audit_kind(
        self,
        audit_kind: str,
    ) -> str:
        return AUDIT_SOURCE_BY_KIND.get(str(audit_kind or "").lower(), "")

    def has_recent_move_to_host(
        self,
        *,
        lines: list[str],
        insert_index: int,
        group: str,
        host: str,
    ) -> bool:
        target_group = str(group or "").upper()
        target_host = str(host or "").upper()

        start = max(0, insert_index - UPDATE_FINAL_LOOKBACK_DUPLICATE_LIMIT)

        for index in range(start, insert_index):
            logical = self.fixed_format.logical(lines[index])
            match = MOVE_TO_DCL_OF_REFERENCE_PATTERN.match(logical)

            if not match:
                continue

            found_group = str(match.group("group") or "").upper()
            found_host = str(match.group("host") or "").upper()

            if found_group == target_group and found_host == target_host:
                return True

        return False

    def unique_targets(
        self,
        values: list[tuple[str, str, str]],
    ) -> list[tuple[str, str, str]]:
        output: list[tuple[str, str, str]] = []
        seen: set[tuple[str, str, str]] = set()

        for group, host, audit_kind in values:
            key = (
                str(group or "").upper(),
                str(host or "").upper(),
                str(audit_kind or "").lower(),
            )

            if not key[0] or not key[1] or not key[2]:
                continue

            if key in seen:
                continue

            seen.add(key)
            output.append(key)

        return output