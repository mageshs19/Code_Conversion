from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.update_char_literal_patterns import (
    END_EXEC_PATTERN,
    EXEC_SQL_START_PATTERN,
    MOVE_NUMLIT_ONLY_PATTERN,
    MOVE_NUMLIT_TO_HOST_OF_GROUP_PATTERN,
    TO_HOST_OF_GROUP_PATTERN,
)
from rules.update_char_literal_rules import (
    CHAR_DB2_TYPE_PREFIXES,
    CHAR_LITERAL_QUOTED_DIAGNOSTIC,
    CHAR_PICTURE_PREFIX,
)


class UpdateCharLiteralQuoter:
    """Quotes bare numeric literals moved into CHAR/VARCHAR DB2 host variables.

    Update-postprocess only. Does not touch retrieval.

    Generic + DCLGEN-driven:
    - Builds a {host_name: is_char} map from parsed DCLGEN columns.
    - CHAR is detected from the DCLGEN db2_type (CHAR/VARCHAR...) or the COBOL
      picture (PIC X...).
    - Rewrites non-SQL "MOVE <digits> TO <host> OF <DCLGROUP>" (one-line and
      wrapped forms) to "MOVE '<digits>' ..." only when the host is CHAR.
    - Never touches SQL host references inside EXEC SQL ... END-EXEC blocks.
    - No hardcoded program, table, column, DCLGEN group, or host variable names.
    """

    def __init__(self, dclgen_columns: list) -> None:
        self._char_hosts = self._build_char_host_map(dclgen_columns)

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #
    def apply(
        self,
        text: str,
        diagnostics: list[str] | None = None,
    ) -> str:
        if not text or not self._char_hosts:
            return text or ""

        lines = (
            str(text)
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .split("\n")
        )

        output: list[str] = []
        in_exec_sql = False
        changed = False
        index = 0

        while index < len(lines):
            line = lines[index]
            logical = self._logical(line)
            upper = logical.upper()

            # Track EXEC SQL blocks; never modify inside them.
            if EXEC_SQL_START_PATTERN.match(logical):
                # One-line EXEC SQL ... END-EXEC. does not open a block.
                if "END-EXEC" not in upper:
                    in_exec_sql = True
                output.append(line)
                index += 1
                continue

            if in_exec_sql:
                output.append(line)
                if END_EXEC_PATTERN.match(logical):
                    in_exec_sql = False
                index += 1
                continue

            # (1) One-line: MOVE <digits> TO <host> OF <DCLGROUP>
            one = MOVE_NUMLIT_TO_HOST_OF_GROUP_PATTERN.match(logical)
            if one and self._is_char_host(one.group("host")):
                literal = one.group("literal")
                host = one.group("host").upper()
                group = one.group("group").upper()
                new_body = f"MOVE '{literal}' TO {host} OF {group}"
                output.append(self._replace_body(line, new_body))
                changed = True
                index += 1
                continue

            # (2) Wrapped: current line "MOVE <digits>", next line
            #     "TO <host> OF <DCLGROUP>".
            move_only = MOVE_NUMLIT_ONLY_PATTERN.match(logical)
            if move_only and index + 1 < len(lines):
                next_logical = self._logical(lines[index + 1])
                nxt = TO_HOST_OF_GROUP_PATTERN.match(next_logical)
                if nxt and self._is_char_host(nxt.group("host")):
                    literal = move_only.group("literal")
                    output.append(
                        self._replace_body(line, f"MOVE '{literal}'")
                    )
                    output.append(lines[index + 1])
                    changed = True
                    index += 2
                    continue

            output.append(line)
            index += 1

        if changed and diagnostics is not None:
            diagnostics.append(CHAR_LITERAL_QUOTED_DIAGNOSTIC)

        return "\n".join(output).rstrip() + "\n"

    # ------------------------------------------------------------------ #
    # CHAR host map (DCLGEN-driven)
    # ------------------------------------------------------------------ #
    def _build_char_host_map(self, dclgen_columns: list) -> dict[str, bool]:
        mapping: dict[str, bool] = {}
        for column in dclgen_columns or []:
            host = NameNormalizer.normalize(
                getattr(column, "cobol_host_name", "")
            )
            if not host:
                continue
            db2_type = str(getattr(column, "db2_type", "") or "")
            picture = str(getattr(column, "cobol_picture", "") or "")
            if self._is_char_datatype(db2_type) or self._is_char_picture(
                picture
            ):
                mapping[host.upper()] = True
        return mapping

    def _is_char_host(self, host: str) -> bool:
        key = NameNormalizer.normalize(host).upper()
        return self._char_hosts.get(key, False)

    def _is_char_datatype(self, db2_type: str) -> bool:
        compact = str(db2_type or "").upper().replace(" ", "")
        return compact.startswith(CHAR_DB2_TYPE_PREFIXES)

    def _is_char_picture(self, picture: str) -> bool:
        cleaned = str(picture or "").strip().upper().lstrip("(")
        # Drop a leading "PIC " if present.
        if cleaned.startswith("PIC "):
            cleaned = cleaned[4:].strip()
        return cleaned.startswith(CHAR_PICTURE_PREFIX)

    # ------------------------------------------------------------------ #
    # Fixed-format line helpers (80-col aware)
    # ------------------------------------------------------------------ #
    BODY_WIDTH = 65

    def _logical(self, line: str) -> str:
        text = str(line or "").rstrip("\n")
        if len(text) >= 72 and text[:6].strip().isdigit():
            return text[7:72].strip()
        if len(text) > 6 and text[:6].strip().isdigit():
            body = text[7:] if len(text) > 7 else ""
            if len(body) >= 8 and body[-8:].strip().isdigit():
                body = body[:-8]
            return body.strip()
        return text.strip()

    def _replace_body(self, line: str, body: str) -> str:
        text = str(line or "").rstrip("\n")
        clean = str(body or "")[: self.BODY_WIDTH].ljust(self.BODY_WIDTH)
        if len(text) >= 72 and text[:6].strip().isdigit():
            left = text[:6]
            right = text[72:80] if len(text) >= 80 else ""
            return f"{left} {clean} {right}"
        if len(text) > 6 and text[:6].strip().isdigit():
            left = text[:6]
            return f"{left} {clean.rstrip()}"
        return clean.rstrip()