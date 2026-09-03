from idms_db2_phase2.domain.models import IdmsOperation
from idms_db2_phase2.parsers.base_text_parser import BaseTextParser
from patterns.cobol_patterns import PROGRAM_ID_PATTERN
from patterns.idms_patterns import (
    ERASE_PATTERN,
    FIND_FIRST_PATTERN,
    MODIFY_PATTERN,
    OBTAIN_CALC_PATTERN,
    OBTAIN_CALC_REVERSED_PATTERN,
    OBTAIN_FIRST_NEXT_PATTERN,
    OBTAIN_OWNER_PATTERN,
    READY_UPDATE_PATTERN,
    STORE_PATTERN,
)


class CobolParser(BaseTextParser):
    """
    Parses IDMS COBOL source and identifies IDMS database operations.

    This parser does not convert COBOL. It only identifies operations for
    later transformation, generation, diagnostics, and validation.

    Regex patterns are stored in patterns/cobol_patterns.py and
    patterns/idms_patterns.py.
    """

    def program_id(
        self,
        cobol_text: str,
    ) -> str:
        match = PROGRAM_ID_PATTERN.search(cobol_text or "")

        if not match:
            return ""

        return match.group(1).upper()

    def analyze(
        self,
        cobol_text: str,
    ) -> list[IdmsOperation]:
        operations: list[IdmsOperation] = []

        for line_number, line in enumerate(
            str(cobol_text or "").splitlines(),
            start=1,
        ):
            clean_line = self._strip_sequence_area(line)
            upper = clean_line.upper()

            operation = self._operation_from_line(
                line=clean_line,
                upper=upper,
                line_number=line_number,
            )

            if operation is not None:
                operations.append(operation)

        return operations

    def _strip_sequence_area(
        self,
        line: str,
    ) -> str:
        """Remove COBOL fixed-format sequence areas from a raw line.

        Self-contained so this parser does not depend on an external helper
        being present on the base class. Handles:
        - columns 1-6 : left sequence number (six leading digits)
        - column 7    : comment/debug indicators ('*', '/')
        Falls back to the base-class helper when available, otherwise uses a
        conservative built-in implementation.
        """
        # Prefer the shared base-class helper if it exists (keeps behavior
        # identical to the rest of the project), but never fail if it does not.
        base_helper = getattr(super(), "strip_sequence_area", None)
        if callable(base_helper):
            try:
                return base_helper(line)
            except Exception:
                pass

        text = str(line or "").rstrip()

        if len(text) > 6:
            indicator = text[6:7]
            if indicator in ("*", "/"):
                return indicator
            if text[:6].strip().isdigit():
                return text[6:]

        return text

    def _operation_from_line(
        self,
        line: str,
        upper: str,
        line_number: int,
    ) -> IdmsOperation | None:
        match = OBTAIN_CALC_PATTERN.search(upper)

        if match:
            return IdmsOperation(
                operation="OBTAIN_CALC",
                record_name=match.group("record").upper(),
                line_number=line_number,
                raw_line=line,
            )

        match = OBTAIN_CALC_REVERSED_PATTERN.search(upper)

        if match:
            return IdmsOperation(
                operation="OBTAIN_CALC",
                record_name=match.group("record").upper(),
                line_number=line_number,
                raw_line=line,
            )

        match = OBTAIN_FIRST_NEXT_PATTERN.search(upper)

        if match:
            return IdmsOperation(
                operation=f"OBTAIN_{match.group('mode').upper()}",
                record_name=match.group("record").upper(),
                set_name=match.group("set").upper(),
                line_number=line_number,
                raw_line=line,
            )

        match = OBTAIN_OWNER_PATTERN.search(upper)

        if match:
            return IdmsOperation(
                operation="OBTAIN_OWNER",
                set_name=match.group("set").upper(),
                line_number=line_number,
                raw_line=line,
            )

        match = FIND_FIRST_PATTERN.search(upper)

        if match:
            return IdmsOperation(
                operation="FIND_FIRST",
                record_name=(match.group("record") or "").upper(),
                set_name=match.group("set").upper(),
                line_number=line_number,
                raw_line=line,
            )

        match = STORE_PATTERN.search(upper)

        if match:
            return IdmsOperation(
                operation="STORE",
                record_name=match.group("record").upper(),
                line_number=line_number,
                raw_line=line,
            )

        match = MODIFY_PATTERN.search(upper)

        if match:
            return IdmsOperation(
                operation="MODIFY",
                record_name=match.group("record").upper(),
                line_number=line_number,
                raw_line=line,
            )

        match = ERASE_PATTERN.search(upper)

        if match:
            return IdmsOperation(
                operation="ERASE",
                record_name=match.group("record").upper(),
                line_number=line_number,
                raw_line=line,
            )

        match = READY_UPDATE_PATTERN.search(upper)

        if match:
            return IdmsOperation(
                operation="READY_UPDATE",
                record_name=match.group("record").upper(),
                line_number=line_number,
                raw_line=line,
            )

        return None


__all__ = [
    "CobolParser",
]