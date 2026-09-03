from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer
from patterns.update_date_host_patterns import (
    END_EXEC_PATTERN,
    EXEC_SQL_START_PATTERN,
    MOVE_SOURCE_ONLY_PATTERN,
    MOVE_TO_HOST_OF_GROUP_PATTERN,
    TO_HOST_OF_GROUP_PATTERN,
)
from rules.sql_generation_rules import DB2_DATE_NULL_SENTINEL


class UpdateDateHostConverter:
    """Converts raw moves into DB2 DATE host variables to the manual date form.

    Update-postprocess only. Does not touch retrieval.

    A DB2 DATE column (DCLGEN db2_type == DATE, stored as PIC X(10)) must
    receive its value through the DD.MM.CCYY realignment, not a raw MOVE.
    TIMESTAMP columns are NOT date columns (they receive a formatted
    TS-TIMESTAMP) and are excluded.

    Finds:
        MOVE <source> TO <DATE-host> OF <DCLGROUP>
    where <source> is a plain field (not DA-DD-MM-CCYY, not TS-TIMESTAMP,
    not a literal) and <DATE-host> is a DCLGEN DATE column, and replaces it
    with the manual conversion block.

    Guards:
    - Only DATE hosts (DCLGEN db2_type == DATE) are converted.
    - TIMESTAMP / TIME columns are excluded.
    - Audit hosts (TS-UPDATE, TS-CREATE, ID-USERID, NR-USERID) are excluded.
    - Sources TS-TIMESTAMP / CS-PROGRAM are excluded.
    - Already-realigned moves (source == DA-DD-MM-CCYY) are skipped.
    - EXEC SQL host references are never touched.
    - No program, record, table, DCLGEN, or host name is hardcoded.
    """

    _ALREADY_REALIGNED_SOURCE = "DADDMMCCYY"
    _PROTECTED_SOURCES = ("TSTIMESTAMP", "CSPROGRAM")
    _AUDIT_HOST_PREFIXES = ("TSUPDATE", "TSCREATE", "IDUSERID", "NRUSERID")

    def __init__(self, dclgen_columns: list) -> None:
        self._date_hosts = self._build_date_host_map(dclgen_columns)

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #
    def apply(
        self,
        text: str,
        diagnostics: list[str] | None = None,
    ) -> str:
        if not text or not self._date_hosts:
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

            if EXEC_SQL_START_PATTERN.match(logical):
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

            # (1) One-line: MOVE <source> TO <host> OF <DCLGROUP>
            one = MOVE_TO_HOST_OF_GROUP_PATTERN.match(logical)
            if one:
                source = one.group("source").strip()
                host = one.group("host").upper()
                group = one.group("group").upper()
                if self._should_convert(host, source):
                    output.extend(
                        self._conversion_lines(line, source, host, group)
                    )
                    changed = True
                    index += 1
                    continue

            # (2) Wrapped: "MOVE <source>" + next "TO <host> OF <DCLGROUP>"
            move_only = MOVE_SOURCE_ONLY_PATTERN.match(logical)
            if move_only and index + 1 < len(lines):
                next_logical = self._logical(lines[index + 1])
                nxt = TO_HOST_OF_GROUP_PATTERN.match(next_logical)
                if nxt:
                    source = move_only.group("source").strip()
                    host = nxt.group("host").upper()
                    group = nxt.group("group").upper()
                    if self._should_convert(host, source):
                        output.extend(
                            self._conversion_lines(line, source, host, group)
                        )
                        changed = True
                        index += 2
                        continue

            output.append(line)
            index += 1

        if changed and diagnostics is not None:
            diagnostics.append(
                "Update date host: converted raw move into DB2 DATE host "
                "to DD.MM.CCYY realignment form."
            )

        return "\n".join(output).rstrip() + "\n"

    # ------------------------------------------------------------------ #
    # Decision + generation
    # ------------------------------------------------------------------ #
    def _should_convert(self, host: str, source: str) -> bool:
        if not self._is_date_host(host):
            return False

        host_key = NameNormalizer.normalize(host).upper().replace("-", "")
        if host_key.startswith(self._AUDIT_HOST_PREFIXES):
            return False

        src_key = NameNormalizer.normalize(source).upper().replace("-", "")
        if src_key == self._ALREADY_REALIGNED_SOURCE:
            return False
        if src_key in self._PROTECTED_SOURCES:
            return False
        if not source or source[0].isdigit() or source.startswith("'"):
            return False
        return True

    def _conversion_lines(
        self,
        reference_line: str,
        source: str,
        host: str,
        group: str,
    ) -> list[str]:
        host_ref = f"{host} OF {group}"
        bodies = [
            "MOVE ZEROES TO DA-CCYYMMDD",
            f"MOVE {source} TO DA-CCYYMMDD",
            "IF DA-CCYYMMDD = ZERO OR DA-CCYYMMDD = SPACES",
            f"    MOVE {DB2_DATE_NULL_SENTINEL} TO DA-CCYYMMDD",
            "END-IF",
            "MOVE CORR DA-CCYYMMDD-R TO DA-DD-MM-CCYY",
            f"MOVE DA-DD-MM-CCYY TO {host_ref}",
        ]
        return [self._replace_body(reference_line, b) for b in bodies]

    # ------------------------------------------------------------------ #
    # DATE host map (DCLGEN-driven)
    # ------------------------------------------------------------------ #
    def _build_date_host_map(self, dclgen_columns: list) -> dict[str, bool]:
        mapping: dict[str, bool] = {}
        for column in dclgen_columns or []:
            host = NameNormalizer.normalize(
                getattr(column, "cobol_host_name", "")
            )
            if not host:
                continue
            db2_type = str(getattr(column, "db2_type", "") or "")
            if self._is_date_datatype(db2_type):
                mapping[host.upper()] = True
        return mapping

    def _is_date_host(self, host: str) -> bool:
        key = NameNormalizer.normalize(host).upper()
        return self._date_hosts.get(key, False)

    def _is_date_datatype(self, db2_type: str) -> bool:
        compact = str(db2_type or "").upper().replace(" ", "")
        # DATE only. TIMESTAMP/TIME columns receive a formatted timestamp,
        # NOT a DD.MM.CCYY date, so they must be excluded.
        if compact.startswith("TIMESTAMP") or compact.startswith("TIME"):
            return False
        return compact.startswith("DATE")

    # ------------------------------------------------------------------ #
    # Fixed-format helpers
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