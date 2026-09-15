# LOCATION: tools/rules_probe.py
# ACTION: CREATE NEW FILE
"""Developer probe: verify every `from rules.X import (...)` name exists.

Run from the project root:

    $env:PYTHONPATH = "src;."
    python tools\rules_probe.py

Exit codes: 0 all names resolve, 1 one or more are missing.
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

for _candidate in (PROJECT_ROOT, SRC_DIR):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

SCAN_DIRS = ("src", "rules", "patterns", "catalogs", "code_review")
WATCHED_PACKAGES = ("rules", "patterns", "catalogs")


def missing_names() -> list[str]:
    problems: list[str] = []
    cache: dict[str, object] = {}

    for folder in SCAN_DIRS:
        base = PROJECT_ROOT / folder
        if not base.exists():
            continue

        for path in sorted(base.rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError as exc:
                problems.append(f"{path} -> syntax error: {exc}")
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                module = node.module or ""
                if not module.startswith(WATCHED_PACKAGES):
                    continue

                if module not in cache:
                    try:
                        cache[module] = importlib.import_module(module)
                    except Exception as exc:  # noqa: BLE001
                        problems.append(f"{path} -> cannot import {module}: {exc}")
                        cache[module] = None

                target = cache.get(module)
                if target is None:
                    continue

                for alias in node.names:
                    if alias.name == "*":
                        continue
                    if not hasattr(target, alias.name):
                        problems.append(
                            f"{path} -> {module}.{alias.name} does not exist"
                        )

    return problems


def main() -> None:
    problems = missing_names()

    if not problems:
        print("rules/patterns/catalogs imports OK")
        raise SystemExit(0)

    for problem in problems:
        print(problem)
    print(f"\n{len(problems)} missing name(s)")
    raise SystemExit(1)


if __name__ == "__main__":
    main()