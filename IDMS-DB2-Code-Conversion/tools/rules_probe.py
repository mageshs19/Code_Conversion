# LOCATION: tools/rules_probe.py
# ACTION: REPLACE ENTIRE FILE

"""Developer probe: verify every `from rules.X import (...)` name exists.

Scans the project for imports from rules/, patterns/ and catalogs/, then
checks that each imported name actually exists in the target module.

Catches the exact failure class that has cost this project several
round-trips: a constant referenced by a composer or generator but never
declared in its rules file, which only surfaces at runtime as

    ImportError: cannot import name 'COMMENT_BLOCK_TEMPLATE' from
    'rules.cursor_paragraph_rules'

BOM HANDLING
------------
Several source files in this project are saved as UTF-8 WITH a byte order
mark. Python imports them without complaint because the import machinery
uses utf-8-sig, but ast.parse() on text read as plain utf-8 fails with

    invalid non-printable character U+FEFF

That is a reader defect, not a source defect, so this probe reads with
utf-8-sig and reports a BOM separately as a hygiene note.

Run from the project root:

    $env:PYTHONPATH = "src;."
    python tools\\rules_probe.py

Exit codes: 0 all names resolve, 1 one or more are missing.
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

# ---------------------------------------------------------------------
# Path bootstrap. Must run before any project import, because running
# "python tools\rules_probe.py" puts only tools\ on sys.path.
# ---------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

for _candidate in (PROJECT_ROOT, SRC_DIR):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

SCAN_DIRS = ("src", "rules", "patterns", "catalogs", "code_review", "tests")
WATCHED_PACKAGES = ("rules", "patterns", "catalogs")

SKIP_DIR_NAMES = {
    "__pycache__",
    ".venv",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
}

# Reading with utf-8-sig strips a leading BOM transparently.
SOURCE_ENCODING = "utf-8-sig"
BOM = "\ufeff"


def _python_files() -> list[Path]:
    files: list[Path] = []

    for folder in SCAN_DIRS:
        base = PROJECT_ROOT / folder
        if not base.exists():
            continue

        for path in sorted(base.rglob("*.py")):
            if any(part in SKIP_DIR_NAMES for part in path.parts):
                continue
            files.append(path)

    return files


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _read_source(path: Path) -> str:
    """Read a source file, stripping any byte order mark."""
    text = path.read_text(encoding=SOURCE_ENCODING, errors="replace")
    return text.lstrip(BOM)


def _has_bom(path: Path) -> bool:
    try:
        return path.read_bytes()[:3] == b"\xef\xbb\xbf"
    except OSError:
        return False


def missing_names() -> tuple[list[str], list[str]]:
    """Return (problems, bom_files)."""
    problems: list[str] = []
    bom_files: list[str] = []
    cache: dict[str, object] = {}

    for path in _python_files():
        if _has_bom(path):
            bom_files.append(_relative(path))

        try:
            tree = ast.parse(_read_source(path), filename=str(path))
        except SyntaxError as exc:
            problems.append(f"{_relative(path)} -> syntax error: {exc}")
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
                    problems.append(
                        f"{_relative(path)} -> cannot import {module}: {exc}"
                    )
                    cache[module] = None

            target = cache.get(module)
            if target is None:
                continue

            for alias in node.names:
                if alias.name == "*":
                    continue
                if not hasattr(target, alias.name):
                    problems.append(
                        f"{_relative(path)} -> "
                        f"{module}.{alias.name} does not exist"
                    )

    return problems, bom_files


def unused_modules() -> list[str]:
    """Rules / patterns / catalogs modules nothing imports from.

    Informational. A brand new rules file that nothing consumes usually
    means the wiring step was missed.
    """
    imported: set[str] = set()

    for path in _python_files():
        try:
            tree = ast.parse(_read_source(path), filename=str(path))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)

    orphans: list[str] = []

    for package in WATCHED_PACKAGES:
        base = PROJECT_ROOT / package
        if not base.exists():
            continue

        for path in sorted(base.rglob("*.py")):
            if path.name == "__init__.py":
                continue
            if any(part in SKIP_DIR_NAMES for part in path.parts):
                continue

            module = (
                path.relative_to(PROJECT_ROOT)
                .with_suffix("")
                .as_posix()
                .replace("/", ".")
            )
            if module not in imported:
                orphans.append(module)

    return orphans


def misplaced_rules_modules() -> list[str]:
    """Files named *_rules.py sitting under patterns/.

    The Clean Architecture Rule puts regex in patterns/ and business or
    layout constants in rules/. A rules file under patterns/ is drift.
    """
    base = PROJECT_ROOT / "patterns"
    if not base.exists():
        return []

    return [
        _relative(path)
        for path in sorted(base.rglob("*_rules.py"))
        if not any(part in SKIP_DIR_NAMES for part in path.parts)
    ]


def main() -> None:
    problems, bom_files = missing_names()
    orphans = unused_modules()
    misplaced = misplaced_rules_modules()

    if orphans:
        print("Modules nothing imports from (informational):")
        for module in orphans:
            print(f"  {module}")
        print("")

    if misplaced:
        print("Rules files under patterns/ (architecture drift):")
        for module in misplaced:
            print(f"  {module}")
        print("")

    if bom_files:
        print("Files saved with a UTF-8 BOM (hygiene only, imports fine):")
        for module in bom_files:
            print(f"  {module}")
        print("")

    if not problems:
        print("rules / patterns / catalogs imports OK")
        raise SystemExit(0)

    print("MISSING NAMES")
    print("-" * 60)
    for problem in problems:
        print(problem)
    print("-" * 60)
    print(f"{len(problems)} problem(s)")
    raise SystemExit(1)


if __name__ == "__main__":
    main()