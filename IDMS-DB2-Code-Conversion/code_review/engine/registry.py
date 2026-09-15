"""Auto-discovers checks. Drop a module in code_review/checks to add one."""

from __future__ import annotations

import importlib
import inspect
import pkgutil

from code_review.engine.check_base import Check

try:
    from code_review.standards.pipeline import CHECK_ORDER, DISABLED_CHECKS, ENABLED_CHECKS
except ImportError:
    CHECK_ORDER, DISABLED_CHECKS, ENABLED_CHECKS = (), frozenset(), ()

PACKAGE = "code_review.checks"


def _classes() -> list[type[Check]]:
    package = importlib.import_module(PACKAGE)
    found = []
    for info in pkgutil.iter_modules(list(package.__path__)):
        if info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{PACKAGE}.{info.name}")
        for _, member in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(member, Check)
                and member is not Check
                and member.__module__ == module.__name__
                and member.CHECK_ID
            ):
                found.append(member)
    return found


def _enabled(check_id: str) -> bool:
    if check_id in DISABLED_CHECKS:
        return False
    return check_id in ENABLED_CHECKS if ENABLED_CHECKS else True


def _key(check: Check):
    if CHECK_ORDER and check.CHECK_ID in CHECK_ORDER:
        return (CHECK_ORDER.index(check.CHECK_ID), check.CHECK_ID)
    return (check.ORDER or 9999, check.CHECK_ID)


def load_checks() -> list[Check]:
    unique = {c.CHECK_ID: c() for c in _classes() if _enabled(c.CHECK_ID)}
    return sorted(unique.values(), key=_key)


def check_ids() -> list[str]:
    return [c.CHECK_ID for c in load_checks()]