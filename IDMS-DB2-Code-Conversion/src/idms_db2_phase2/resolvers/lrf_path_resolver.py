# LOCATION: src/idms_db2_phase2/resolvers/lrf_path_resolver.py
# ACTION: REPLACE ENTIRE FILE
"""Turns an LRF path keyword into a concrete access plan.

NAME FORM
---------
Every name this module returns is rendered in COBOL form (UPPERCASE with
hyphens), because the expander writes them straight back into COBOL
source. NameNormalizer.normalize() is deliberately NOT used: it produces
the DB2 column form (underscores) and would emit VMBTL03_R01.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rules.lrf_conversion_rules import (
    STATUS_END_OF_SET,
    STATUS_NOT_FOUND,
    STATUS_SET_EMPTY,
)

RETURN_PREFIX = "RETURN "


def cobol_name(value: str) -> str:
    """UPPERCASE COBOL/IDMS form: hyphens, never underscores."""
    return str(value or "").strip().upper().replace("_", "-")


@dataclass
class LrfAccessStep:
    """One renderable IDMS access line."""

    verb: str = ""
    scope: str = ""
    record_name: str = ""
    within_name: str = ""
    where_clause: str = ""

    @property
    def is_renderable(self) -> bool:
        return bool(self.record_name and self.within_name)


@dataclass
class LrfAccessPlan:
    """Everything the expander needs for one path keyword."""

    keyword: str = ""
    logical_record: str = ""
    path_group_verb: str = ""
    parent: LrfAccessStep | None = None
    driving: LrfAccessStep | None = None
    end_of_set_literals: set[str] = field(default_factory=set)
    not_found_literals: set[str] = field(default_factory=set)
    element_records: list[str] = field(default_factory=list)

    @property
    def is_usable(self) -> bool:
        return bool(self.driving and self.driving.is_renderable)


class LrfPathResolver:
    """Resolves a path keyword into an LrfAccessPlan."""

    def __init__(
        self,
        *,
        lrf_repository=None,
        mapping_repository=None,
    ) -> None:
        self.lrf_repository = lrf_repository
        self.mapping_repository = mapping_repository
        self.messages: list[str] = []

    # ---------------------------------------------------------- public
    def is_empty(self) -> bool:
        if self.lrf_repository is None:
            return True
        try:
            return bool(self.lrf_repository.is_empty())
        except Exception:  # noqa: BLE001
            return True

    def plan_for_keyword(self, keyword: str) -> LrfAccessPlan | None:
        if self.is_empty():
            return None

        try:
            path = self.lrf_repository.path_for_keyword(keyword)
        except Exception:  # noqa: BLE001
            return None

        if path is None:
            return None

        plan = LrfAccessPlan(
            keyword=cobol_name(path.keyword),
            logical_record=cobol_name(path.logical_record),
            path_group_verb=str(path.path_group_verb or "").upper(),
            element_records=[
                cobol_name(name)
                for name in self._element_records(path.logical_record)
            ],
        )

        steps: list[LrfAccessStep] = []

        for command in path.commands or []:
            self._collect_literals(command, plan)

            verb = str(command.verb or "").upper()
            if verb not in ("OBTAIN", "FIND", "ERASE"):
                continue

            steps.append(
                LrfAccessStep(
                    verb=verb,
                    scope=str(command.scope or "").upper(),
                    record_name=cobol_name(command.record_name),
                    within_name=cobol_name(command.within_name),
                    where_clause=str(command.where_clause or "").strip(),
                )
            )

        if not steps:
            return plan

        renderable = [step for step in steps if step.is_renderable]
        if renderable:
            plan.driving = renderable[-1]
            if len(renderable) > 1:
                plan.parent = renderable[0]
        else:
            plan.driving = steps[-1]

        return plan

    def record_is_mapped(self, record_name: str) -> bool:
        """True when Sheet Mapping knows this IDMS record."""
        if self.mapping_repository is None:
            return True

        record = cobol_name(record_name)
        if not record:
            return False

        for probe in (
            "db2_table_for_record",
            "table_for_record",
            "has_record",
            "record_exists",
        ):
            method = getattr(self.mapping_repository, probe, None)
            if method is None:
                continue
            try:
                result = method(record)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(result, bool):
                return result
            if isinstance(result, str):
                return bool(result.strip())

        return True

    # --------------------------------------------------------- helpers
    def _element_records(self, logical_record_name: str) -> list:
        try:
            return self.lrf_repository.element_records(logical_record_name) or []
        except Exception:  # noqa: BLE001
            return []

    @staticmethod
    def _collect_literals(command, plan: LrfAccessPlan) -> None:
        actions = getattr(command, "status_actions", None) or {}
        for status, action in actions.items():
            literal = LrfPathResolver._return_literal(action)
            if not literal:
                continue
            if str(status) == STATUS_END_OF_SET:
                plan.end_of_set_literals.add(literal)
            elif str(status) in (STATUS_NOT_FOUND, STATUS_SET_EMPTY):
                plan.not_found_literals.add(literal)

    @staticmethod
    def _return_literal(action: str) -> str:
        text = str(action or "").strip().upper()
        if not text.startswith(RETURN_PREFIX):
            return ""
        return cobol_name(text[len(RETURN_PREFIX):])


__all__ = ["LrfAccessStep", "LrfAccessPlan", "LrfPathResolver", "cobol_name"]