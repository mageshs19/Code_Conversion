# LOCATION: src/idms_db2_phase2/transformers/lrf_path_expander.py
# ACTION: REPLACE ENTIRE FILE
"""Expands LRF syntax into the classic IDMS syntax the converter knows.

NO-LRF CONTRACT
---------------
With no logical record metadata, or with metadata but no LRF syntax in the
program, expand() returns the source text byte-for-byte. The converter
therefore behaves exactly as it did before LRF support existed.

NAME FORM
---------
Generated names are COBOL form (UPPERCASE, hyphens). NameNormalizer is not
used here: normalize() yields DB2 column form and would emit VMBTL03_R01.

COMMENT FORM
------------
A generated comment line carries '*' in the indicator column and its
marker starts immediately at column 8, so the output reads

      *DB2: Expanded LRF ...
      *DB2-KEEP: ...

which matches the marker text declared in rules/.
"""

from __future__ import annotations

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from patterns.lrf_program_patterns import (
    BARE_OF_LR_PATTERN,
    LR_ERASE_WHERE_PATTERN,
    LR_OBTAIN_WHERE_PATTERN,
    LR_STATUS_CONDITION_PATTERN,
    LR_STATUS_TOKEN_PATTERN,
    OF_LR_SUFFIX_PATTERN,
)
from rules.lrf_conversion_rules import (
    ENABLE_LRF_PATH_EXPANSION,
    END_OF_SET_TOKEN,
    EXPANDED_OBTAIN_TEMPLATE,
    EXPANDED_PARENT_TEMPLATE,
    FIND_FIRST_TEMPLATE,
    LRF_EXPANSION_MESSAGES,
    OBTAIN_FIRST_TEMPLATE,
    OBTAIN_NEXT_TEMPLATE,
    RECORD_NOT_FOUND_TOKEN,
    REQUIRE_MAPPED_DRIVING_RECORD,
    SKIPPED_NO_PATH_TEMPLATE,
    SKIPPED_NO_RECORD_TEMPLATE,
    SKIPPED_UNMAPPED_TEMPLATE,
    STATEMENT_TERMINATOR,
)

PROCEDURE_DIVISION_TOKEN = "PROCEDURE DIVISION"
COMMENT_INDICATORS = ("*", "/", "D", "-")
COMMENT_PREFIX_COLUMNS = "      "
MODE_NEXT = "NEXT"
DEFAULT_INDENT = "    "


def cobol_name(value: str) -> str:
    """UPPERCASE COBOL/IDMS form: hyphens, never underscores."""
    return str(value or "").strip().upper().replace("_", "-")


class LrfPathExpander:
    """Rewrites LRF program syntax into classic IDMS syntax."""

    def __init__(
        self,
        *,
        path_resolver=None,
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.path_resolver = path_resolver
        self.fixed_format = fixed_format or FixedFormatLineService()
        self.messages: list[str] = []

    # ---------------------------------------------------------- public
    def expand(self, cobol_text: str) -> str:
        self.messages = []

        text = str(cobol_text or "")
        if not text.strip() or not ENABLE_LRF_PATH_EXPANSION:
            return text

        if self.path_resolver is None or self.path_resolver.is_empty():
            if self._contains_lrf_syntax(text):
                self._log("no_logical_records")
            return text

        if not self._contains_lrf_syntax(text):
            return text

        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

        output: list[str] = []
        in_procedure = False
        expanded = 0
        skipped = 0
        status_rewrites = 0
        qualifier_strips = 0

        for line in lines:
            logical = self._logical(line)
            upper = logical.upper()

            if PROCEDURE_DIVISION_TOKEN in upper:
                in_procedure = True
                output.append(line)
                continue

            if not in_procedure or self._is_comment(line) or not logical:
                output.append(line)
                continue

            obtain = LR_OBTAIN_WHERE_PATTERN.match(logical)
            if obtain:
                rendered, ok = self._expand_obtain(line, obtain)
                output.extend(rendered)
                expanded += 1 if ok else 0
                skipped += 0 if ok else 1
                continue

            erase = LR_ERASE_WHERE_PATTERN.match(logical)
            if erase:
                rendered, ok = self._expand_erase(line, erase)
                output.extend(rendered)
                expanded += 1 if ok else 0
                skipped += 0 if ok else 1
                continue

            new_logical, hits = self._rewrite_lr_status(logical)
            status_rewrites += hits

            new_logical, strips = self._strip_of_lr(new_logical)
            qualifier_strips += strips

            if new_logical != logical:
                output.append(self._replace_body(line, new_logical))
            else:
                output.append(line)

        if status_rewrites:
            self._log("status_rewritten", count=status_rewrites)
        if qualifier_strips:
            self._log("qualifier_stripped", count=qualifier_strips)
        if expanded or skipped:
            self._log("summary", expanded=expanded, skipped=skipped)

        if not (expanded or skipped or status_rewrites or qualifier_strips):
            return text

        return "\n".join(output).rstrip() + "\n"

    # ------------------------------------------------------- expansion
    def _expand_obtain(self, line: str, match) -> tuple[list[str], bool]:
        mode = str(match.group("mode") or "").upper()
        lr_name = cobol_name(match.group("lr"))
        keyword = cobol_name(match.group("keyword"))

        plan = self.path_resolver.plan_for_keyword(keyword)

        if plan is None:
            self._log("keyword_not_found", keyword=keyword)
            return self._keep(
                line, SKIPPED_NO_PATH_TEMPLATE.format(keyword=keyword)
            ), False

        if not plan.is_usable:
            self._log("keyword_not_found", keyword=keyword)
            return self._keep(
                line, SKIPPED_NO_RECORD_TEMPLATE.format(keyword=keyword)
            ), False

        record = plan.driving.record_name
        within = plan.driving.within_name

        if REQUIRE_MAPPED_DRIVING_RECORD and not self.path_resolver.record_is_mapped(record):
            self._log("record_unmapped", record=record, keyword=keyword)
            return self._keep(
                line, SKIPPED_UNMAPPED_TEMPLATE.format(record=record)
            ), False

        rendered: list[str] = []
        rendered.extend(
            self._comment(line, EXPANDED_OBTAIN_TEMPLATE.format(
                mode=mode, lr=lr_name, keyword=keyword,
                record=record, within=within,
            ))
        )

        if plan.parent is not None and mode != MODE_NEXT:
            parent = plan.parent
            rendered.extend(
                self._comment(line, EXPANDED_PARENT_TEMPLATE.format(
                    keyword=keyword, record=parent.record_name,
                ))
            )
            rendered.extend(
                self._statement(line, FIND_FIRST_TEMPLATE.format(
                    record=parent.record_name,
                    within=parent.within_name,
                ))
            )
            self._log(
                "parent_emitted",
                record=parent.record_name,
                within=parent.within_name,
                keyword=keyword,
            )

        template = (
            OBTAIN_NEXT_TEMPLATE if mode == MODE_NEXT
            else OBTAIN_FIRST_TEMPLATE
        )
        rendered.extend(
            self._statement(line, template.format(record=record, within=within))
        )

        self._log(
            "expanded",
            mode=mode, lr=lr_name, keyword=keyword,
            record=record, within=within,
        )
        return rendered, True

    def _expand_erase(self, line: str, match) -> tuple[list[str], bool]:
        keyword = cobol_name(match.group("keyword"))
        plan = self.path_resolver.plan_for_keyword(keyword)

        if plan is None or not plan.is_usable:
            self._log("keyword_not_found", keyword=keyword)
            return self._keep(
                line, SKIPPED_NO_PATH_TEMPLATE.format(keyword=keyword)
            ), False

        record = plan.driving.record_name

        if REQUIRE_MAPPED_DRIVING_RECORD and not self.path_resolver.record_is_mapped(record):
            self._log("record_unmapped", record=record, keyword=keyword)
            return self._keep(
                line, SKIPPED_UNMAPPED_TEMPLATE.format(record=record)
            ), False

        rendered = self._comment(line, EXPANDED_OBTAIN_TEMPLATE.format(
            mode="ERASE", lr=plan.logical_record, keyword=keyword,
            record=record, within=plan.driving.within_name,
        ))
        rendered.extend(self._statement(line, f"ERASE {record}"))
        return rendered, True

    # ------------------------------------------------ status/qualifier
    @staticmethod
    def _rewrite_lr_status(logical: str) -> tuple[str, int]:
        hits = 0

        def _replace(match) -> str:
            nonlocal hits
            hits += 1
            operator = str(match.group("operator") or "").upper()
            literal = cobol_name(match.group("literal"))
            token = (
                RECORD_NOT_FOUND_TOKEN
                if "NOT-FND" in literal or "NOT-FOUND" in literal
                else END_OF_SET_TOKEN
            )
            return f"NOT {token}" if operator.startswith("NOT") else token

        return LR_STATUS_CONDITION_PATTERN.sub(_replace, logical), hits

    @staticmethod
    def _strip_of_lr(logical: str) -> tuple[str, int]:
        first, a = OF_LR_SUFFIX_PATTERN.subn(r"\g<head>", logical)
        second, b = BARE_OF_LR_PATTERN.subn("", first)
        return second, a + b

    # ---------------------------------------------------------- render
    def _statement(self, template_line: str, body: str) -> list[str]:
        text = body.rstrip()
        if not text.endswith(STATEMENT_TERMINATOR):
            text = f"{text}{STATEMENT_TERMINATOR}"
        indent = self._body_indent(template_line)
        return self._emit(template_line, f"{indent}{text}", indicator=" ")

    def _comment(self, template_line: str, body: str) -> list[str]:
        """Comment body starts at column 8 - no indent, no leading star."""
        text = str(body or "").lstrip("*").strip()
        return self._emit(template_line, text, indicator="*")

    def _keep(self, line: str, marker: str) -> list[str]:
        rendered = self._comment(line, marker)
        rendered.extend(self._comment(line, self._logical(line)))
        return rendered

    def _emit(self, template_line: str, body: str, indicator: str) -> list[str]:
        if not self._is_fixed(template_line):
            if indicator == "*":
                return [f"{COMMENT_PREFIX_COLUMNS}*{body}"]
            return [body]

        left, _ind, _old, right = self.fixed_format.split(template_line)
        try:
            return self.fixed_format.emit(left, indicator, body, right)
        except Exception:  # noqa: BLE001
            return [template_line]

    def _replace_body(self, line: str, new_body: str) -> str:
        indent = self._body_indent(line)
        text = f"{indent}{new_body.strip()}"
        if not self._is_fixed(line):
            return text
        return self.fixed_format.replace_body(line, text)

    # --------------------------------------------------------- helpers
    def _logical(self, line: str) -> str:
        try:
            return str(self.fixed_format.logical(line) or "").strip()
        except Exception:  # noqa: BLE001
            return str(line or "").strip()

    def _is_fixed(self, line: str) -> bool:
        try:
            return bool(self.fixed_format.is_fixed_line(line))
        except Exception:  # noqa: BLE001
            return False

    def _body_indent(self, line: str) -> str:
        if not self._is_fixed(line):
            text = str(line or "")
            return " " * (len(text) - len(text.lstrip(" ")))
        try:
            _l, _i, body, _r = self.fixed_format.split(line)
            return " " * (len(body) - len(body.lstrip(" ")))
        except Exception:  # noqa: BLE001
            return DEFAULT_INDENT

    @staticmethod
    def _is_comment(line: str) -> bool:
        text = str(line or "")
        if len(text) >= 7 and text[:6].strip().isdigit():
            return text[6] in COMMENT_INDICATORS
        return text.lstrip().startswith(COMMENT_INDICATORS)

    @staticmethod
    def _contains_lrf_syntax(text: str) -> bool:
        upper = str(text or "").upper()
        if LR_STATUS_TOKEN_PATTERN.search(upper):
            return True
        if " OF LR" in upper:
            return True
        for line in upper.splitlines():
            if LR_OBTAIN_WHERE_PATTERN.match(line.strip()):
                return True
            if LR_ERASE_WHERE_PATTERN.match(line.strip()):
                return True
        return False

    def _log(self, key: str, **values) -> None:
        template = LRF_EXPANSION_MESSAGES.get(key, "")
        if template:
            self.messages.append(template.format(**values))


__all__ = ["LrfPathExpander", "cobol_name"]