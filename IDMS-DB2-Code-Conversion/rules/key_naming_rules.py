# LOCATION: rules/key_naming_rules.py
# ACTION: CREATE NEW FILE - single source of truth
"""Column-name prefix vocabulary. Constants only."""

from __future__ import annotations

# Surrogate / sequence identity key prefixes. A column carrying one of
# these is unique on its own, so it alone gives a total order.
IDENTITY_KEY_PREFIXES = (
    "NS_ID",
    "NR_ID",
    "ID_",
    "CO_ID",
    "NR_IS",
)

__all__ = ["IDENTITY_KEY_PREFIXES"]