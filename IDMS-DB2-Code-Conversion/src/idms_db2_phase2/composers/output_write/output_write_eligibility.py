# LOCATION: src/idms_db2_phase2/composers/output_write/output_write_eligibility.py
# ACTION: CREATE NEW FILE
"""Decides whether one candidate block may be extracted.

Every gate REFUSES rather than guesses. A refusal leaves working COBOL
and, where it is worth reporting, a diagnostic; a guess produces source
the compiler rejects or a WRITE that fires the wrong number of times.

THE GATES, IN ORDER

    1  exactly one WRITE          two writes is a business decision
    2  enough executable lines    a one-line body is not worth a paragraph
    3  not already extracted      an earlier pass may have done it
    4  the paragraph name is free never shadow an existing paragraph
"""

from __future__ import annotations

from dataclasses import dataclass, field

from idms_db2_phase2.composers.output_write.output_write_block_finder import (
    CandidateBlock,
)
from idms_db2_phase2.composers.output_write.output_write_line_utils import (
    OutputWriteLineUtils,
)
from idms_db2_phase2.composers.output_write.output_write_scanner import (
    OutputWriteScanner,
)
from idms_db2_phase2.services.name_normalizer import NameNormalizer
from rules.output_write_paragraph_rules import (
    MINIMUM_BODY_LINES,
    REQUIRED_WRITE_COUNT,
    WRITE_PARAGRAPH_TEMPLATE,
)


@dataclass(frozen=True)
class Refusal:
    """A named diagnostic plus its template values.

    An empty key means 'refuse silently' - the block simply is not a
    candidate, and saying so on every IF in the program would drown the
    validation log.
    """

    key: str = ""
    values: dict = field(default_factory=dict)

    @property
    def is_reportable(self) -> bool:
        return bool(self.key)


@dataclass(frozen=True)
class ExtractionPlan:
    """An accepted block and the paragraph it will become."""

    block: CandidateBlock
    paragraph: str = ""
    record: str = ""
    body: list[str] = field(default_factory=list)


class OutputWriteEligibility:
    """All accept / refuse decisions for one candidate block."""

    def __init__(
        self,
        line_utils: OutputWriteLineUtils | None = None,
        scanner: OutputWriteScanner | None = None,
    ) -> None:
        self.lines = line_utils or OutputWriteLineUtils()
        self.scanner = scanner or OutputWriteScanner(self.lines)

    # ----------------------------------------------------------- public
    def assess(
        self,
        lines: list[str],
        block: CandidateBlock,
        existing: set[str],
    ) -> tuple[ExtractionPlan | None, Refusal | None]:
        """(plan, refusal). Exactly one of the two is None."""
        body = block.body(lines)

        writes = self.scanner.write_records(body)
        if len(writes) != REQUIRED_WRITE_COUNT:
            return None, self._wrong_write_count(block, writes)

        if len(self.lines.executable_lines(body)) < MINIMUM_BODY_LINES:
            return None, Refusal(
                "skipped_too_small",
                {"source": block.source},
            )

        if self.scanner.already_extracted(body):
            return None, Refusal()

        record = NameNormalizer.to_cobol(writes[0])
        paragraph = WRITE_PARAGRAPH_TEMPLATE.format(record=record)

        if paragraph in existing:
            return None, Refusal(
                "skipped_name_taken",
                {"paragraph": paragraph},
            )

        return (
            ExtractionPlan(
                block=block,
                paragraph=paragraph,
                record=record,
                body=body,
            ),
            None,
        )

    # ---------------------------------------------------------- helpers
    @staticmethod
    def _wrong_write_count(
        block: CandidateBlock,
        writes: list[str],
    ) -> Refusal:
        """Two WRITEs is worth reporting; zero is just an ordinary IF."""
        if not writes:
            return Refusal()
        return Refusal(
            "skipped_multiple_writes",
            {"source": block.source, "count": len(writes)},
        )


__all__ = ["ExtractionPlan", "OutputWriteEligibility", "Refusal"]