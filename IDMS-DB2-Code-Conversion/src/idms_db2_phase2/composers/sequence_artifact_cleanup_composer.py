# LOCATION: src/idms_db2_phase2/composers/sequence_artifact_cleanup_composer.py
# ACTION: CREATE NEW FILE

"""Sequence artifact cleanup composer.

Removes lines whose COBOL body is nothing but a leaked source sequence
number, and repairs the sentence the removal exposes.

Symptom
-------
    002480     STOP RUN.
    002490     001690/.                <-- not COBOL
    002500 HOOFDVERWERKING.

The original source carried a page-eject line:

    001690/

A formatting pass that did not recognise the short, unsequenced form
treated the WHOLE line as COBOL text. The left sequence number and the
indicator became the body, and the paragraph terminator pass then added
a period, producing '001690/.'.

Consequences if left in place
-----------------------------
- The compiler rejects the statement.
- OutputWritePlacementCleanup cannot match a trailing
  IF ... WRITE ... END-IF block, because the artifact sits between the
  END-IF and the paragraph boundary. The guarded output write is then
  never relocated out of the child-row paragraph, and the WRITE fires
  once per fetched child row instead of once per parent row.

Why this runs late
------------------
The artifact is produced AFTER CobolCleanupComposer, by one of the
layout passes. Dropping it inside ParagraphTerminatorCleanup is too
early. This composer therefore runs immediately after
composers["fixed_format"], where every line is sequenced and no further
pass will reintroduce the shape.

Repair
------
Removing the artifact can leave the preceding statement unterminated,
because the artifact was carrying the period:

    003040     END-IF
    003050     002190/.        <-- removed

This composer therefore walks back to the last executable line of the
paragraph and restores the sentence terminator when it is missing.

Clean Architecture
------------------
- Constants live in rules/sequence_artifact_rules.py.
- Line geometry and artifact detection come from FixedFormatLineService.
- No regex is defined here.
- No program, paragraph, record, table, cursor or host variable name is
  hardcoded.
"""

from __future__ import annotations

from idms_db2_phase2.services.fixed_format_line_service import (
    FixedFormatLineService,
)
from rules.sequence_artifact_rules import (
    ENFORCE_SEQUENCE_ARTIFACT_CLEANUP,
    PARAGRAPH_TERMINATOR,
    REPAIR_EXPOSED_SENTENCE,
    SENTENCE_CARRIERS,
    SEQUENCE_ARTIFACT_MESSAGES,
)


class SequenceArtifactCleanupComposer:
    """Drops leaked sequence-number lines and repairs the sentence."""

    def __init__(
        self,
        fixed_format: FixedFormatLineService | None = None,
    ) -> None:
        self.fixed_format = fixed_format or FixedFormatLineService()
        self.messages: list[str] = []

    # =================================================================
    # Public entry point
    # =================================================================
    def compose(self, text: str) -> str:
        self.messages = []

        if not text or not ENFORCE_SEQUENCE_ARTIFACT_CLEANUP:
            return str(text or "")

        lines = (
            str(text)
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .split("\n")
        )

        output: list[str] = []
        removed = 0
        repaired = 0

        for line in lines:
            if not self.fixed_format.is_sequence_artifact(line):
                output.append(line)
                continue

            removed += 1
            self.messages.append(
                SEQUENCE_ARTIFACT_MESSAGES["removed"].format(
                    body=self.fixed_format.logical(line)
                )
            )

            if REPAIR_EXPOSED_SENTENCE and self._terminate_previous(output):
                repaired += 1

        if removed:
            self.messages.append(
                SEQUENCE_ARTIFACT_MESSAGES["summary"].format(
                    removed=removed,
                    repaired=repaired,
                )
            )

        return "\n".join(output).rstrip() + "\n"

    # =================================================================
    # Sentence repair
    # =================================================================
    def _terminate_previous(self, output: list[str]) -> bool:
        """Close the sentence the removed artifact was carrying.

        Walks back over blank, comment, page-eject and debug lines to the
        last executable statement. Adds a period only when the statement
        is a recognised sentence carrier and does not already end in one.
        """
        for index in range(len(output) - 1, -1, -1):
            line = output[index]

            if self.fixed_format.is_comment_or_control_line(line):
                continue

            logical = self.fixed_format.logical(line)
            if not logical:
                continue

            if logical.endswith(PARAGRAPH_TERMINATOR):
                return False

            first_word = logical.split()[0].upper() if logical.split() else ""
            if first_word not in SENTENCE_CARRIERS:
                return False

            new_body = self.fixed_format.body(line).rstrip()
            rebuilt = self.fixed_format.replace_body(
                line,
                new_body + PARAGRAPH_TERMINATOR,
            )

            if rebuilt == line:
                return False

            output[index] = rebuilt
            self.messages.append(
                SEQUENCE_ARTIFACT_MESSAGES["terminated"].format(
                    statement=logical
                )
            )
            return True

        return False