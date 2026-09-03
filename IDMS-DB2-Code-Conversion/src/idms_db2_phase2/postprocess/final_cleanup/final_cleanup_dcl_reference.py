from __future__ import annotations

from patterns.update_final_cleanup_patterns import (
    END_EXEC_PATTERN,
    EXEC_SQL_PATTERN,
    MOVE_TO_DCL_DOT_REFERENCE_PATTERN,
    NON_SQL_DCL_DOT_REFERENCE_STRICT_PATTERN,
    TO_DCL_DOT_REFERENCE_PATTERN,
)
from rules.update_cobol_final_cleanup_rules import (
    FINAL_CLEANUP_AREA_B,
    FINAL_CLEANUP_BODY_WIDTH,
    FINAL_CLEANUP_DCL_PREFIX,
    FINAL_CLEANUP_FIELD_OF_GROUP_TEMPLATE,
    FINAL_CLEANUP_MOVE_TEMPLATE,
    FINAL_CLEANUP_TOKEN_END_EXEC,
    FINAL_CLEANUP_TOKEN_MOVE,
    FINAL_CLEANUP_TOKEN_TO,
    FINAL_CLEANUP_TO_FIELD_OF_GROUP_TEMPLATE,
)


class FinalCleanupDclReference:
    """Rewrites non-SQL DCLGROUP.FIELD references to FIELD OF DCLGROUP."""

    def _rewrite_non_sql_dcl_dot_references(self, lines: list[str]) -> list[str]:
        output: list[str] = []
        in_exec_sql = False

        for line in lines:
            logical = self._logical(line)
            upper = logical.upper()

            if EXEC_SQL_PATTERN.match(logical):
                if FINAL_CLEANUP_TOKEN_END_EXEC in upper:
                    output.append(line)
                    continue
                in_exec_sql = True
                output.append(line)
                continue

            if in_exec_sql:
                output.append(line)
                if END_EXEC_PATTERN.match(logical):
                    in_exec_sql = False
                continue

            move_match = MOVE_TO_DCL_DOT_REFERENCE_PATTERN.match(logical)
            if move_match:
                source = str(move_match.group("source")).strip()
                field = move_match.group("field").upper()
                group = move_match.group("group").upper()
                output.append(
                    self._replace_body(
                        line, FINAL_CLEANUP_MOVE_TEMPLATE.format(source=source)
                    )
                )
                output.append(
                    self._replace_body(
                        line,
                        FINAL_CLEANUP_TO_FIELD_OF_GROUP_TEMPLATE.format(
                            field=field, group=group
                        ),
                    )
                )
                continue

            to_match = TO_DCL_DOT_REFERENCE_PATTERN.match(logical)
            if to_match:
                field = to_match.group("field").upper()
                group = to_match.group("group").upper()
                output.append(
                    self._replace_body(
                        line,
                        FINAL_CLEANUP_TO_FIELD_OF_GROUP_TEMPLATE.format(
                            field=field, group=group
                        ),
                    )
                )
                continue

            move_rewrite = self._rewrite_move_to_dcl_dot_as_lines(original_line=line)
            if move_rewrite:
                output.extend(move_rewrite)
                continue

            body = self._body(line)
            rewritten_body = NON_SQL_DCL_DOT_REFERENCE_STRICT_PATTERN.sub(
                lambda match: FINAL_CLEANUP_FIELD_OF_GROUP_TEMPLATE.format(
                    field=match.group("field").upper(),
                    group=match.group("group").upper(),
                ),
                body,
            )
            if rewritten_body != body:
                output.append(self._replace_body(line, rewritten_body))
                continue

            output.append(line)

        return output

    def _rewrite_move_to_dcl_dot_as_lines(self, original_line: str) -> list[str]:
        body = self._body(original_line).rstrip()
        stripped = body.strip()
        upper = stripped.upper()

        if not upper.startswith(FINAL_CLEANUP_TOKEN_MOVE):
            return []
        if FINAL_CLEANUP_TOKEN_TO not in upper:
            return []

        before_to, after_to = self._split_last_to(stripped)
        if not before_to or not after_to or "." not in after_to:
            return []

        group, field = after_to.split(".", 1)
        group = group.strip().upper()
        field = field.strip().upper()

        trailing_period = ""
        if field.endswith("."):
            trailing_period = "."
            field = field[:-1].strip()

        if not group.startswith(FINAL_CLEANUP_DCL_PREFIX) or not field:
            return []

        leading = body[: len(body) - len(body.lstrip(" "))]
        if not leading:
            leading = FINAL_CLEANUP_AREA_B

        first_body = f"{leading}{before_to}"
        second_body = f"{leading}TO {field} OF {group}{trailing_period}"
        one_line = f"{leading}{before_to} TO {field} OF {group}{trailing_period}"

        if len(one_line) <= FINAL_CLEANUP_BODY_WIDTH:
            return [self._replace_body(original_line, one_line)]

        return [
            self._replace_body(original_line, first_body),
            self._replace_body(original_line, second_body),
        ]

    def _split_last_to(self, text: str) -> tuple[str, str]:
        upper = str(text or "").upper()
        marker = FINAL_CLEANUP_TOKEN_TO
        index = upper.rfind(marker)
        if index < 0:
            return "", ""
        return text[:index].strip(), text[index + len(marker):].strip()