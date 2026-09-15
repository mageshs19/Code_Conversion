"""CHK-15 Nested cursor processing."""

from __future__ import annotations

from code_review.engine import cursors, sql_blocks as sql
from code_review.engine.check_base import MAJOR, RETRIEVAL, Check
from code_review.standards import cobol_standards as std


class NestedCursorProcessingCheck(Check):
    CHECK_ID = "CHK-15"
    TITLE = "Nested cursor processing"
    SEVERITY = MAJOR
    APPLIES_TO = RETRIEVAL
    ORDER = 150

    def relevant(self, ctx, view) -> bool:
        return len(cursors.paragraph_sets(view)) > 1

    def not_relevant_reason(self) -> str:
        return "Program uses fewer than two cursors."

    def review(self, ctx, view, record):
        sets = cursors.paragraph_sets(view)
        parents, children = self._split(sets)
        performed = cursors.performed_names(view)

        # ---- 01 child cursors are numbered above the threshold ------
        record.expect(
            "01",
            f"Nested cursors are numbered at or above "
            f"{std.CHILD_CURSOR_MINIMUM_NUMBER}",
            bool(children),
            note=(
                f"{len(sets)} cursor(s) found, none numbered at or above "
                f"{std.CHILD_CURSOR_MINIMUM_NUMBER}."
            ),
        )

        # ---- 02 every cursor set is complete ------------------------
        incomplete = []
        for name, group in sorted(sets.items()):
            for operation in std.CURSOR_OPERATIONS:
                if operation not in group:
                    incomplete.append(f"{name} {operation}")
        record.expect_all(
            "02", "Every nested cursor has a complete paragraph set",
            incomplete,
        )

        # ---- 03 every child cursor is closed ------------------------
        if not children:
            record.skip(
                "03", "Every nested cursor is closed",
                "No nested cursor found.",
            )
        else:
            record.expect_all(
                "03", "Every nested cursor is closed",
                [
                    group["CLOSE"].name
                    for group in children.values()
                    if "CLOSE" in group
                    and group["CLOSE"].name not in performed
                ],
            )

        # ---- 04 parent and child use distinct flags -----------------
        flags = [
            f"{name}{std.CURSOR_EOC_SUFFIX}" for name in sorted(sets)
        ]
        record.expect(
            "04", "Parent and nested cursors use distinct flags",
            len(set(flags)) == len(flags),
            note=f"flags: {', '.join(flags)}",
        )

        # ---- 05 each cursor is opened exactly once ------------------
        repeated = []
        for name, group in sorted(sets.items()):
            open_para = group.get("OPEN")
            if open_para is None:
                continue
            count = len(performed.get(open_para.name, []))
            if count > 1:
                repeated.append(f"{open_para.name} performed {count} times")
        record.expect_all(
            "05", "Each cursor is opened from exactly one place", repeated,
        )

        # ---- 06 child fetch loop has an early stop ------------------
        if not std.ENFORCE_CHILD_FETCH_EARLY_STOP:
            record.skip(
                "06", "Nested fetch loops carry an early-stop condition",
                "Early-stop condition not yet agreed (decision open).",
            )
        elif not children:
            record.skip(
                "06", "Nested fetch loops carry an early-stop condition",
                "No nested cursor found.",
            )
        else:
            code = [sql.norm(line.logical) for line in view.code]
            missing = []
            for group in children.values():
                fetch = group.get("FETCH")
                if fetch is None:
                    continue
                loop = f"PERFORM {fetch.name} UNTIL"
                found = any(
                    line.startswith(loop)
                    and std.CHILD_FETCH_EARLY_STOP_FIELD in line
                    for line in code
                )
                if not found:
                    missing.append(fetch.name)
            record.expect_all(
                "06", "Nested fetch loops carry an early-stop condition",
                missing,
            )

    # ---- helpers ----------------------------------------------------
    @staticmethod
    def _split(sets):
        parents, children = {}, {}
        for name, group in sets.items():
            open_para = group.get("OPEN")
            number = open_para.number if open_para else 0
            if number >= std.CHILD_CURSOR_MINIMUM_NUMBER:
                children[name] = group
            else:
                parents[name] = group
        return parents, children