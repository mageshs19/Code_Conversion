"""CHK-21 Unresolved restart metadata safe skip."""

from __future__ import annotations

from code_review.engine import metadata as meta, sql_blocks as sql
from code_review.engine.check_base import CRITICAL, UPDATE, Check
from code_review.standards import cobol_standards as std


class RestartSafeSkipCheck(Check):
    """Certifies that a deferred restart conversion was deferred safely.

    The authority rule is absolute: the converter must never invent a DB2
    name. When the restart table is absent from the supplied metadata the
    correct behaviour is to skip, document the skip, and leave the legacy
    IDMS flow untouched. This check proves that happened, which is what
    turns decision D-3 from an undocumented gap into an auditable one.
    """

    CHECK_ID = "CHK-21"
    TITLE = "Unresolved restart metadata safe skip"
    SEVERITY = CRITICAL
    APPLIES_TO = UPDATE
    ORDER = 210

    def relevant(self, ctx, view) -> bool:
        return bool(
            self._restart_in_source(ctx) or self._restart_blocks(view)
        )

    def not_relevant_reason(self) -> str:
        return "Program has no restart or control record."

    def review(self, ctx, view, record):
        resolved = self._resolved_restart_tables(ctx)
        blocks = self._restart_blocks(view)
        generated = bool(blocks)

        # ---- 01 no fabrication --------------------------------------
        if resolved:
            record.skip(
                "01", "No restart SQL is generated without metadata",
                f"Restart table {', '.join(sorted(resolved))} is resolved "
                f"in the supplied metadata, so generation is authorised.",
            )
        elif not ctx.has_metadata:
            record.skip(
                "01", "No restart SQL is generated without metadata",
                "No Sheet Mapping or DCLGEN metadata supplied for this run.",
            )
        else:
            record.expect_none(
                "01", "No restart SQL is generated without metadata", blocks,
            )

        # ---- 02 the skip is documented ------------------------------
        if generated:
            record.skip(
                "02", "The restart skip is documented in the output",
                "Restart flow was generated, so no skip is expected.",
            )
        else:
            record.expect(
                "02", "The restart skip is documented in the output",
                self._skip_documented(view),
                note="No restart skip comment found. A silent skip leaves "
                     "the reader unable to tell converted from deferred.",
            )

        # ---- 03 the legacy flow is preserved ------------------------
        if generated:
            record.skip(
                "03", "The legacy restart flow is preserved",
                "Restart flow was generated, so replacement is expected.",
            )
        elif not ctx.has_source:
            record.skip(
                "03", "The legacy restart flow is preserved",
                "No source program supplied for comparison.",
            )
        else:
            record.expect_all(
                "03", "The legacy restart flow is preserved",
                self._lost_restart_tokens(ctx, view),
            )

        # ---- 04 no half-built restart paragraph set -----------------
        present = [
            name for name in std.RESTART_PARAGRAPHS.values()
            if view.paragraph_exists(name)
        ]
        if not present:
            record.ok("04", "No partial restart paragraph set was emitted")
        else:
            record.expect_all(
                "04", "No partial restart paragraph set was emitted",
                sorted(set(std.RESTART_PARAGRAPHS.values()) - set(present)),
            )

        # ---- 05 no warning marker remains in code -------------------
        record.expect_none(
            "05", "No unresolved-metadata warning marker remains in code",
            [
                line for line in view.code
                if any(m in line.logical for m in std.FORBIDDEN_MARKERS)
            ],
        )

    # ---- helpers ----------------------------------------------------
    @staticmethod
    def _restart_blocks(view) -> list:
        """Generated SQL that reads or writes a restart or control table."""
        return [
            block for block in sql.sql_blocks(view)
            if block.verb in std.RESTART_SQL_OPERATIONS
            and sql.targets_restart(block, std.RESTART_TABLE_NAME_HINTS)
        ]

    @staticmethod
    def _resolved_restart_tables(ctx) -> set[str]:
        """Restart tables the supplied metadata actually confirms."""
        known = meta.dclgen_tables(ctx) | meta.mapped_tables(ctx)
        return {
            table for table in known
            if any(
                hint in table for hint in std.RESTART_TABLE_NAME_HINTS
            )
        }

    @staticmethod
    def _restart_tokens(text: str) -> set[str]:
        upper = sql.norm(text)
        return {
            hint for hint in std.RESTART_CONTROL_HINTS if hint in upper
        }

    @classmethod
    def _restart_in_source(cls, ctx) -> set[str]:
        return cls._restart_tokens(ctx.source_cobol)

    @staticmethod
    def _skip_documented(view) -> bool:
        return any(
            marker in line.logical
            for line in view.comments
            for marker in std.RESTART_SKIP_MARKERS
        )

    @classmethod
    def _lost_restart_tokens(cls, ctx, view) -> list[str]:
        """Restart markers present in the source but gone from the output.

        When nothing was generated the legacy flow must survive intact.
        A token that vanished means the converter removed working logic
        without replacing it.
        """
        output = view.all_text
        return sorted(
            token for token in cls._restart_in_source(ctx)
            if token not in output
        )