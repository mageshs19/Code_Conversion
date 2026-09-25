# LOCATION: tests/test_rules_no_duplicate_constants.py
# ACTION: REPLACE ENTIRE FILE
"""A module-level name assigned twice is a silent, order-dependent bug."""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

import pytest

from rules import cursor_declaration_rules

RULES_DIR = Path(cursor_declaration_rules.__file__).parent
RULE_FILES = sorted(p for p in RULES_DIR.glob("*.py") if p.name != "__init__.py")


def _module_level_assignments(path: Path) -> Counter:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: Counter = Counter()
    for node in tree.body:                      # module level ONLY
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                names[target.id] += 1
    return names


@pytest.mark.parametrize("path", RULE_FILES, ids=lambda p: p.name)
def test_no_rule_constant_is_assigned_twice(path: Path) -> None:
    duplicates = {n: c for n, c in _module_level_assignments(path).items() if c > 1}
    assert not duplicates, f"{path.name} assigns twice: {sorted(duplicates)}"


def test_order_by_message_catalogues_do_not_collide() -> None:
    """The resolver merges both dicts; a shared key would shadow one."""
    shared = set(cursor_declaration_rules.ORDER_BY_KEY_MESSAGES) & set(
        cursor_declaration_rules.CURSOR_ORDER_BY_MESSAGES
    )
    assert not shared, f"colliding ORDER BY message keys: {sorted(shared)}"


def test_every_key_width_message_has_the_placeholders_the_resolver_supplies() -> None:
    from string import Formatter

    supplied = {
        "single_key": {"record", "columns"},
        "narrowed_to_identity": {"record", "total", "kept", "columns"},
        "kept_composite": {"record", "total"},
        "kept_composite_child": {"record", "total"},
    }
    for key, template in cursor_declaration_rules.ORDER_BY_KEY_MESSAGES.items():
        required = {f for _, f, _, _ in Formatter().parse(template) if f}
        assert required <= supplied[key], f"{key} wants unsupplied {required - supplied[key]}"


def test_queryno_first_matches_the_manual_reference() -> None:
    order = cursor_declaration_rules.QUERYNO_FIRST_ORDER
    rendered = cursor_declaration_rules.QUERYNO_BASE + (
        order * cursor_declaration_rules.QUERYNO_STEP
    )
    assert rendered == cursor_declaration_rules.QUERYNO_FIRST


def test_queryno_template_keeps_the_number_placeholder() -> None:
    """cursor_declare_builder renders with .format(number=...)."""
    assert "{number}" in cursor_declaration_rules.QUERYNO_TEMPLATE
    assert cursor_declaration_rules.QUERYNO_TEMPLATE.format(number=254) == "QUERYNO 254"


def test_sentinels_are_re_exported_not_redeclared() -> None:
    from rules import record_materialisation_rules

    assert (
        cursor_declaration_rules.NON_COLUMN_SENTINELS
        is record_materialisation_rules.NON_COLUMN_SENTINELS
    )