from __future__ import annotations

from patterns.update_business_sql_patterns import (
    CONTINUE_PATTERN,
    CONVERTED_MODIFY_COMMENT_PATTERN,
    DCL_HOST_GROUP_PATTERN,
    END_EVALUATE_PATTERN,
    END_EXEC_PATTERN,
    EVALUATE_SQLCODE_PATTERN,
    EXEC_SQL_START_PATTERN,
    EXEC_SQL_UPDATE_PATTERN,
    PARAGRAPH_HEADER_PATTERN,
    SQL_LOCATION_UPDATE_PATTERN,
    WHEN_ZERO_PATTERN,
)
from rules.update_business_sql_rules import (
    ADD_UPDATE_COUNTER_TEMPLATE,
    COMMIT_CHECK_IF_TEMPLATE,
    COMMIT_CHECK_PERFORM_TEMPLATE,
    END_IF_STATEMENT,
    FINAL_PERIOD_LINE,
    INITIALIZE_DCL_GROUP_TEMPLATE,
    NESTED_INDENT,
    PERFORM_TEMPLATE,
    SQL_ERROR_PARAGRAPH_NAMES,
    SQL_ERROR_ROUTINE_MARKER,
    TOKEN_INITIALIZE_DCL,
    TOKEN_STAR,
)
from rules.update_restart_rules import (
    RESTART_PARAGRAPH_NAMES,
    UPDATE_COMMIT_THRESHOLD,
    UPDATE_RESTART_DIAGNOSTICS,
    UPDATE_RESTART_WS_NAMES,
)


class UpdateSqlBlockExtractor:
    """Detects and extracts the inline generated UPDATE SQL block.

    Update-postprocess only. Depends on the host class for line rendering
    (_active_line_like / _logical / _is_comment_line), name helpers
    (_update_paragraph_name / _paragraph_exists / _strip_existing_final_period /
    _normalize_update_paragraph_lines), and the shared line_utils.
    Owns no regex and no column geometry; all patterns/constants are external.
    """

    def _extract_inline_update_block(
        self, *, lines, process_paragraph, block_info, diagnostics
    ):
        block_start, block_end, record_name, dcl_group = block_info
        update_paragraph = self._update_paragraph_name(record_name)

        if self._paragraph_exists(lines, update_paragraph):
            return lines

        extracted_block = self._replace_update_success_continue(
            extracted_block=lines[block_start:block_end]
        )
        replacement = self._replacement_in_process(
            reference_line=lines[block_start],
            update_paragraph=update_paragraph,
        )
        updated_lines = lines[:block_start] + replacement + lines[block_end:]

        process_range = self.line_utils.find_paragraph_range(
            updated_lines, process_paragraph
        )
        if process_range:
            p_start, p_end = process_range
            updated_lines = self._ensure_initialize_dcl_group(
                lines=updated_lines, start=p_start, end=p_end, dcl_group=dcl_group
            )

        update_paragraph_lines = self._build_update_paragraph(
            paragraph_name=update_paragraph, extracted_block=extracted_block
        )
        insert_index = self._update_paragraph_insert_index(updated_lines)
        updated_lines = (
            updated_lines[:insert_index]
            + [""]
            + update_paragraph_lines
            + [""]
            + updated_lines[insert_index:]
        )
        diagnostics.append(UPDATE_RESTART_DIAGNOSTICS["business_update_extracted"])
        return updated_lines

    def _find_inline_update_block(self, *, lines, start, end):
        for index in range(start + 1, end):
            logical = self._logical(lines[index])
            comment_match = CONVERTED_MODIFY_COMMENT_PATTERN.match(logical)
            location_match = SQL_LOCATION_UPDATE_PATTERN.match(logical)
            if not comment_match and not location_match:
                continue

            record_name = ""
            if comment_match:
                record_name = str(comment_match.group("record") or "").strip().upper()
            if not record_name and location_match:
                record_name = str(location_match.group("record") or "").strip().upper()
            if not record_name:
                continue

            block_start = index
            if location_match and index > start + 1:
                previous_logical = self._logical(lines[index - 1])
                if CONVERTED_MODIFY_COMMENT_PATTERN.match(previous_logical):
                    block_start = index - 1

            block_end = self._find_sqlcode_evaluate_end(
                lines=lines, start=index, limit=end
            )
            if block_end <= index:
                continue

            dcl_group = self._find_dcl_group(lines=lines[block_start:block_end])
            return block_start, block_end, record_name, dcl_group

        return None

    def _find_sqlcode_evaluate_end(self, *, lines, start, limit):
        seen_exec_sql = seen_update = seen_end_exec = seen_evaluate = False

        for index in range(start, limit):
            logical = self._logical(lines[index])
            if EXEC_SQL_START_PATTERN.match(logical):
                seen_exec_sql = True
                continue
            if seen_exec_sql and EXEC_SQL_UPDATE_PATTERN.match(logical):
                seen_update = True
                continue
            if seen_update and END_EXEC_PATTERN.match(logical):
                seen_end_exec = True
                continue
            if seen_end_exec and EVALUATE_SQLCODE_PATTERN.match(logical):
                seen_evaluate = True
                continue
            if seen_evaluate and END_EVALUATE_PATTERN.match(logical):
                return index + 1

        return -1

    def _replacement_in_process(self, *, reference_line, update_paragraph):
        names = UPDATE_RESTART_WS_NAMES
        return [
            self._active_line_like(
                reference_line=reference_line,
                body=PERFORM_TEMPLATE.format(paragraph=update_paragraph),
            ),
            "",
            self._active_line_like(
                reference_line=reference_line,
                body=COMMIT_CHECK_IF_TEMPLATE.format(
                    counter=names["commit_counter"],
                    threshold=UPDATE_COMMIT_THRESHOLD,
                ),
            ),
            self._active_line_like(
                reference_line=reference_line,
                body=COMMIT_CHECK_PERFORM_TEMPLATE.format(
                    indent=NESTED_INDENT,
                    commit_paragraph=RESTART_PARAGRAPH_NAMES["commit"],
                ),
            ),
            self._active_line_like(
                reference_line=reference_line, body=END_IF_STATEMENT
            ),
        ]

    def _build_update_paragraph(self, *, paragraph_name, extracted_block):
        cleaned_block = self._strip_existing_final_period(extracted_block)
        output = [f"{paragraph_name}.", ""]
        output.extend(cleaned_block)
        output.append(FINAL_PERIOD_LINE)
        return self._normalize_update_paragraph_lines(output)

    def _replace_update_success_continue(self, *, extracted_block):
        names = UPDATE_RESTART_WS_NAMES
        output: list[str] = []
        index = 0

        while index < len(extracted_block):
            line = extracted_block[index]
            logical = self._logical(line)

            if WHEN_ZERO_PATTERN.match(logical):
                output.append(line)
                if index + 1 < len(extracted_block):
                    next_logical = self._logical(extracted_block[index + 1])
                    if CONTINUE_PATTERN.match(next_logical):
                        output.append(
                            self._active_line_like(
                                reference_line=extracted_block[index + 1],
                                body=ADD_UPDATE_COUNTER_TEMPLATE.format(
                                    counter=names["update_counter"]
                                ),
                            )
                        )
                        index += 2
                        continue
                index += 1
                continue

            output.append(line)
            index += 1

        return output

    def _ensure_initialize_dcl_group(self, *, lines, start, end, dcl_group):
        if not dcl_group:
            return lines

        target = f"{TOKEN_INITIALIZE_DCL[:-3]} {dcl_group}".strip()
        for index in range(start, end):
            if self._logical(lines[index]).upper().rstrip(".") == target:
                return lines

        insert_index = self._first_executable_line_index(
            lines=lines, start=start, end=end
        )
        if insert_index < 0:
            return lines

        initialize_line = self._active_line_like(
            reference_line=lines[insert_index],
            body=INITIALIZE_DCL_GROUP_TEMPLATE.format(group=dcl_group),
        )
        return lines[:insert_index] + [initialize_line, ""] + lines[insert_index:]

    def _first_executable_line_index(self, *, lines, start, end):
        for index in range(start + 1, end):
            line = lines[index]
            logical = self._logical(line).strip()
            if not logical or self._is_comment_line(line):
                continue
            if logical.startswith(TOKEN_STAR):
                continue
            if PARAGRAPH_HEADER_PATTERN.match(logical):
                continue
            return index
        return -1

    def _update_paragraph_insert_index(self, lines):
        sqlerror_index = self._find_sqlerror_routine_index(lines)
        if sqlerror_index >= 0:
            return sqlerror_index

        restart_abend_range = self.line_utils.find_paragraph_range(
            lines, RESTART_PARAGRAPH_NAMES["abend"]
        )
        if restart_abend_range:
            return restart_abend_range[1]

        return len(lines)

    def _find_sqlerror_routine_index(self, lines):
        for index, line in enumerate(lines):
            logical = self._logical(line).upper().rstrip(".")
            if logical in set(SQL_ERROR_PARAGRAPH_NAMES):
                return index
            if SQL_ERROR_ROUTINE_MARKER in logical:
                return index
        return -1

    def _find_dcl_group(self, lines):
        for line in lines:
            logical = self._logical(line)
            for match in DCL_HOST_GROUP_PATTERN.finditer(logical):
                group = str(match.group(0) or "").strip().upper()
                if group:
                    return group
        return ""