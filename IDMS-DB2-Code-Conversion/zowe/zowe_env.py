# LOCATION: zowe/zowe_env.py
# ACTION: CREATE NEW FILE
"""Loads .env and resolves values per artifact.

Resolution order for any setting NAME belonging to ARTIFACT:

    1. ZOWE_{ARTIFACT}_{NAME}   artifact specific
    2. ZOWE_{NAME}              shared fallback
    3. supplied default

A blank or absent artifact line therefore INHERITS the shared value.

A value may also reference another key explicitly. A value that is
nothing but a bare ZOWE_ key name is refused, because it is a typo that
would otherwise be sent to the mainframe as a literal user id.
"""

from __future__ import annotations

import os
from pathlib import Path

from zowe.zowe_patterns import (
    BARE_ENV_KEY_PATTERN,
    DOTENV_LINE_PATTERN,
    ENV_REFERENCE_PATTERN,
)
from zowe.zowe_rules import (
    ARTIFACT_KEY_TEMPLATE,
    ENV_REFERENCE_MAX_DEPTH,
    MASKED_VALUE,
    SENSITIVE_NAMES,
    SHARED_KEY_TEMPLATE,
    ZOWE_ERROR_MESSAGES,
)

_DOTENV_LOADED = False


# ---------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------
def load_dotenv_once() -> None:
    """Load the project .env exactly once. Never overwrites a real env var."""
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True

    try:
        from dotenv import find_dotenv, load_dotenv
        load_dotenv(find_dotenv(usecwd=True), override=False)
        return
    except ImportError:
        pass

    for candidate in (
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[1] / ".env",
    ):
        if not candidate.is_file():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            match = DOTENV_LINE_PATTERN.match(line)
            if not match:
                continue
            value = match.group("value").strip().strip('"').strip("'")
            os.environ.setdefault(match.group("key"), value)
        return


# ---------------------------------------------------------------
# Reference resolution
# ---------------------------------------------------------------
def _expand_once(key: str, value: str) -> str:
    """Replace every reference with that key's raw value."""
    missing: list[str] = []

    def replace(match) -> str:
        target = match.group("key") or match.group("bare")
        resolved = os.getenv(target, "").strip()
        if not resolved:
            missing.append(target)
            return ""
        return resolved

    expanded = ENV_REFERENCE_PATTERN.sub(replace, value)

    if missing:
        raise ValueError(
            ZOWE_ERROR_MESSAGES["unresolved_reference"].format(
                key=key, missing=missing[0]
            )
        )
    return expanded


def _resolve_value(key: str, value: str) -> str:
    """Expand references, then refuse a bare key name typed by mistake."""
    resolved = str(value or "").strip()
    if not resolved:
        return ""

    depth = 0
    while ENV_REFERENCE_PATTERN.search(resolved):
        depth += 1
        if depth > ENV_REFERENCE_MAX_DEPTH:
            raise ValueError(
                ZOWE_ERROR_MESSAGES["circular_reference"].format(
                    key=key, depth=ENV_REFERENCE_MAX_DEPTH
                )
            )
        resolved = _expand_once(key, resolved).strip()

    if BARE_ENV_KEY_PATTERN.match(resolved):
        raise ValueError(
            ZOWE_ERROR_MESSAGES["bare_key_reference"].format(
                key=key, value=resolved
            )
        )
    return resolved


def _lookup(key: str) -> str:
    """Raw value for one key, with references expanded."""
    load_dotenv_once()
    return _resolve_value(key, os.getenv(key, ""))


# ---------------------------------------------------------------
# Public API
# ---------------------------------------------------------------
def setting(artifact: str, name: str, default: str = "") -> str:
    """Artifact value, then shared value, then default."""
    scoped = _lookup(ARTIFACT_KEY_TEMPLATE.format(artifact=artifact, name=name))
    if scoped:
        return scoped

    shared = _lookup(SHARED_KEY_TEMPLATE.format(name=name))
    if shared:
        return shared

    return default


def setting_int(artifact: str, name: str, default: int) -> int:
    raw = setting(artifact, name)
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def setting_bool(artifact: str, name: str, default: bool) -> bool:
    raw = setting(artifact, name).lower()
    if raw in ("true", "1", "yes", "y", "on"):
        return True
    if raw in ("false", "0", "no", "n", "off"):
        return False
    return default


def raw_setting(key: str, default: str = "") -> str:
    """A plain key with no artifact scoping, for example ZOWE_LANDING_ROOT."""
    return _lookup(key) or default


def setting_source(artifact: str, name: str) -> str:
    """Which key supplied the value. Used by the show command only."""
    scoped_key = ARTIFACT_KEY_TEMPLATE.format(artifact=artifact, name=name)
    if _lookup(scoped_key):
        return scoped_key

    shared_key = SHARED_KEY_TEMPLATE.format(name=name)
    if _lookup(shared_key):
        return shared_key + " (inherited)"

    return "(default)"


def mask(name: str, value: str) -> str:
    """Never echo a password into a console line or a diagnostic."""
    if not value:
        return "(not set)"
    return MASKED_VALUE if name in SENSITIVE_NAMES else value