# LOCATION: src/idms_db2_phase2/transformers/cobol_program_id_transformer.py
# ACTION: REPLACE ENTIRE FILE
"""Target PROGRAM-ID replacement, PROGRAM-ID period cleanup, and the
PROGRAM-NAME literal rewrite.

CORRECTION 1 - three undefined names
-------------------------------------
`program_name_literal_replacement` referenced
ENFORCE_PROGRAM_NAME_LITERAL, PROGRAM_NAME_LITERAL_MOVE_PATTERN and
PROGRAM_NAME_LITERAL_MESSAGES, none of which were imported. The first
call raised NameError.

The flag and the messages now live in rules/cobol_transformer_rules.py.
The pattern is MOVE_TO_PROGRAM_NAME_PATTERN, which already exists in
patterns/final_feedback_fix_patterns.py - a second, near-identical
pattern would be two definitions of one fact.

CORRECTION 2 - self.messages did not exist
--------------------------------------------
The method appended to `self.messages`, which __init__ never created, so
even a successful match raised AttributeError. The list is now owned
here and cleared by reset(), which callers invoke once per program. One
component factory instance converts a whole folder, so an uncleared list
carries program 1's diagnostics into program 2.

CORRECTION 3 - the terminating period was dropped
---------------------------------------------------
MOVE_TO_PROGRAM_NAME_PATTERN captures three groups:

    prefix  = "MOVE '"
    program = "VM7BD200"
    suffix  = "' TO PROGRAM-NAME."     <- the period lives HERE

Substituting the flat string "MOVE '<target>' TO PROGRAM-NAME" discarded
the suffix, so the statement lost its period and ran into the next one.
The replacement now rebuilds from the captured groups, so whatever
terminator the author wrote is carried through unchanged.

CORRECTION 4 - group name
---------------------------
match.group("literal") - the group is named "program".

RELATIONSHIP TO ProgramNameSyncService
----------------------------------------
That service performs the same rewrite as a WHOLE-TEXT pass, reading the
FINAL PROGRAM-ID out of the converted text. This method is the PER-LINE
form and additionally refuses a literal that is not the source program
id. Run ONE of them, not both: a second pass is a harmless no-op because
the literal already equals the target, but two owners of one rule drift.
"""

from __future__ import annotations

import re

from idms_db2_phase2.transformers.cobol_transformer_line_utils import (
    CobolTransformerLineUtils,
)
from patterns.cobol_patterns import PROGRAM_ID_PATTERN
from patterns.final_feedback_fix_patterns import (
    MOVE_TO_PROGRAM_NAME_PATTERN,
)
from rules.cobol_transformer_rules import (
    ENFORCE_PROGRAM_NAME_LITERAL,
    PROGRAM_NAME_LITERAL_MESSAGES,
)


class CobolProgramIdTransformer:
    """
    Handles target PROGRAM-ID replacement, final PROGRAM-ID period
    cleanup, and the PROGRAM-NAME literal rewrite.
    """

    def __init__(
        self,
        line_utils: CobolTransformerLineUtils | None = None,
    ) -> None:
        self.line_utils = line_utils or CobolTransformerLineUtils()
        # Per-program diagnostics. Cleared by reset().
        self.messages: list[str] = []

    # -----------------------------------------------------------------
    # Per-program lifecycle
    # -----------------------------------------------------------------
    def reset(self) -> None:
        """Clear per-program state.

        One instance converts every program in a folder, so a list that
        is only initialised in __init__ leaks program 1's diagnostics
        into program 2.
        """
        self.messages = []

    # -----------------------------------------------------------------
    # PROGRAM-ID
    # -----------------------------------------------------------------
    def program_id_replacement(
        self,
        *,
        original_line: str,
        logical_line: str,
        target_program_id: str,
    ) -> str | None:
        if not target_program_id:
            return None

        if not PROGRAM_ID_PATTERN.search(logical_line):
            return None

        program_id = str(target_program_id or "").strip().upper()

        if not program_id:
            return None

        replacement_body = f"PROGRAM-ID. {program_id}."

        return self.line_utils.replace_logical_body(
            original_line=original_line,
            replacement_body=replacement_body,
        )

    def fix_program_id_period(
        self,
        *,
        text: str,
        target_program_id: str,
    ) -> str:
        program_id = str(target_program_id or "").strip().upper()

        if program_id:
            pattern = re.compile(
                rf"PROGRAM-ID\.\s*{re.escape(program_id)}\.?",
                flags=re.IGNORECASE,
            )

            return pattern.sub(
                f"PROGRAM-ID. {program_id}.",
                text,
                count=1,
            )

        return re.sub(
            r"(PROGRAM-ID\.\s*[A-Z0-9-]+)\s*$",
            r"\1.",
            text,
            count=1,
            flags=re.IGNORECASE | re.MULTILINE,
        )

    # -----------------------------------------------------------------
    # PROGRAM-NAME
    # -----------------------------------------------------------------
    def program_name_literal_replacement(
        self,
        *,
        original_line: str,
        logical_line: str,
        source_program_id: str,
        target_program_id: str,
    ) -> str | None:
        """Rewrite MOVE '<source-id>' TO PROGRAM-NAME.

        Returns None when the line is not a PROGRAM-NAME move, or when
        the literal is not the source program id - a literal holding a
        business value is never touched.

        The terminator captured in the suffix group is carried through
        unchanged, so a statement written without a period stays without
        one and a statement written with one keeps it.
        """
        if not ENFORCE_PROGRAM_NAME_LITERAL:
            return None

        source = str(source_program_id or "").strip().upper()
        target = str(target_program_id or "").strip().upper()
        if not source or not target or source == target:
            return None

        text = str(logical_line or "")

        match = MOVE_TO_PROGRAM_NAME_PATTERN.search(text)
        if not match:
            return None

        literal = str(match.group("program") or "").strip().upper()
        if literal != source:
            self.messages.append(
                PROGRAM_NAME_LITERAL_MESSAGES["left_unchanged"].format(
                    literal=literal
                )
            )
            return None

        def _replace(found: re.Match) -> str:
            # Rebuild from the captured groups so the author's
            # terminator survives. A flat replacement string drops it.
            return (
                found.group("prefix")
                + target
                + found.group("suffix")
            )

        new_body = MOVE_TO_PROGRAM_NAME_PATTERN.sub(
            _replace,
            text,
            count=1,
        )

        if new_body == text:
            return None

        self.messages.append(
            PROGRAM_NAME_LITERAL_MESSAGES["rewritten"].format(
                old=literal,
                new=target,
            )
        )

        return self.line_utils.replace_logical_body(
            original_line=original_line,
            replacement_body=new_body,
        )


__all__ = [
    "CobolProgramIdTransformer",
]