# LOCATION: src/idms_db2_phase2/generators/counter_generator.py
# ACTION: CREATE NEW FILE
"""Row counter and program-name constant generator.

Closes open decision D-2 in favour of AUTOMATE, per the COBOL team's
manual reference program:

    10  WS-NB-BEFF-COUNT         PIC 9(7)    COMP-3 VALUE ZEROES.
    10  WS-NB-OUTPUT-COUNT       PIC 9(7)    COMP-3 VALUE ZEROES.
    10  CS-PROGRAM               PIC X(8)    VALUE 'VMDZ4420'.
    ...
    ADD 1 TO WS-NB-BEFF-COUNT
    ...
    DISPLAY 'TOTAL BEFF RECORDS   : ' WS-NB-BEFF-COUNT
    DISPLAY 'TOTAL OUTPUT RECORDS : ' WS-NB-OUTPUT-COUNT

Constants live in rules/counter_rules.py. No program, record, table or
cursor name is hardcoded here.
"""

from __future__ import annotations

from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.counter_rules import (
    COUNTER_ADD_TEMPLATE,
    COUNTER_DECLARATION_TEMPLATE,
    COUNTER_DISPLAY_TEMPLATE,
    COUNTER_LABEL_FETCH_TEMPLATE,
    COUNTER_LABEL_OUTPUT,
    COUNTER_LABEL_WIDTH,
    COUNTER_MESSAGES,
    COUNTER_NAME_TEMPLATE,
    COUNTER_PICTURE,
    EMIT_COUNTER_TOTALS,
    EMIT_PROGRAM_NAME_CONSTANT,
    EMIT_ROW_COUNTERS,
    OUTPUT_COUNTER_NAME,
    PROGRAM_CONSTANT_NAME,
    PROGRAM_CONSTANT_TEMPLATE,
    PROGRAM_NAME_MOVE_TEMPLATE,
    PROGRAM_NAME_TARGET_FIELD,
)


class CounterGenerator:
    """Builds counter declarations, increments and end-of-run totals."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    # -----------------------------------------------------------------
    # Naming
    # -----------------------------------------------------------------
    @staticmethod
    def counter_name_for_table(table_name: str) -> str:
        """Derive WS-NB-<token>-COUNT from a DB2 table name.

        DZBEFFTV -> BEFF -> WS-NB-BEFF-COUNT
        The token is the distinctive middle of the table name, with the
        two-character system prefix and the TV/TB suffix removed.
        """
        table = NameNormalizer.normalize(str(table_name or ""))
        if not table:
            return ""

        token = table
        for suffix in ("_TV", "_TB"):
            if token.endswith(suffix):
                token = token[: -len(suffix)]
                break
        else:
            if token.endswith("TV") or token.endswith("TB"):
                token = token[:-2]

        if len(token) > 2:
            token = token[2:]

        token = token.strip("_-")
        if not token:
            return ""

        return COUNTER_NAME_TEMPLATE.format(token=token)

    # -----------------------------------------------------------------
    # WORKING-STORAGE declarations
    # -----------------------------------------------------------------
    def declarations(
        self,
        program_id: str,
        table_names: list[str],
    ) -> list[str]:
        """Lines to append inside the existing 01 work group."""
        self.messages = []
        lines: list[str] = []

        if EMIT_ROW_COUNTERS:
            for name in self._counter_names(table_names):
                lines.append(
                    COUNTER_DECLARATION_TEMPLATE.format(
                        name=name, picture=COUNTER_PICTURE,
                    )
                )
                self.messages.append(
                    COUNTER_MESSAGES["declared_counter"].format(name=name)
                )

        if EMIT_PROGRAM_NAME_CONSTANT and program_id:
            lines.append(
                PROGRAM_CONSTANT_TEMPLATE.format(
                    name=PROGRAM_CONSTANT_NAME,
                    program_id=NameNormalizer.to_cobol(program_id),
                )
            )
            self.messages.append(
                COUNTER_MESSAGES["declared_program_constant"].format(
                    name=PROGRAM_CONSTANT_NAME, program_id=program_id,
                )
            )

        return lines

    # -----------------------------------------------------------------
    # Increments
    # -----------------------------------------------------------------
    @staticmethod
    def increment(counter_name: str) -> str:
        if not EMIT_ROW_COUNTERS or not counter_name:
            return ""
        return COUNTER_ADD_TEMPLATE.format(name=counter_name)

    # -----------------------------------------------------------------
    # Program-name move
    # -----------------------------------------------------------------
    @staticmethod
    def program_name_move() -> str:
        if not EMIT_PROGRAM_NAME_CONSTANT:
            return ""
        return PROGRAM_NAME_MOVE_TEMPLATE.format(
            constant=PROGRAM_CONSTANT_NAME,
            target=PROGRAM_NAME_TARGET_FIELD,
        )

    # -----------------------------------------------------------------
    # End-of-run totals
    # -----------------------------------------------------------------
    def totals(self, table_names: list[str]) -> list[str]:
        if not EMIT_COUNTER_TOTALS:
            return []

        lines: list[str] = []
        for table in table_names:
            name = self.counter_name_for_table(table)
            if not name:
                continue
            token = name.replace("WS-NB-", "").replace("-COUNT", "")
            label = COUNTER_LABEL_FETCH_TEMPLATE.format(token=token)
            lines.append(
                COUNTER_DISPLAY_TEMPLATE.format(
                    label=label.ljust(COUNTER_LABEL_WIDTH), name=name,
                )
            )

        lines.append(
            COUNTER_DISPLAY_TEMPLATE.format(
                label=COUNTER_LABEL_OUTPUT.ljust(COUNTER_LABEL_WIDTH),
                name=OUTPUT_COUNTER_NAME,
            )
        )

        self.messages.append(
            COUNTER_MESSAGES["counter_totals_added"].format(count=len(lines))
        )
        return lines

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    def _counter_names(self, table_names: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()

        for table in table_names:
            name = self.counter_name_for_table(table)
            if name and name not in seen:
                seen.add(name)
                out.append(name)

        if OUTPUT_COUNTER_NAME not in seen:
            out.append(OUTPUT_COUNTER_NAME)

        return out