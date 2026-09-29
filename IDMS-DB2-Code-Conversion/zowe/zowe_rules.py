# LOCATION: zowe/zowe_rules.py
# ACTION: REPLACE ENTIRE FILE
"""Zowe rule constants - facade.

The constants are split across five focused modules. This file re-exports
them all, so every existing

    from zowe.zowe_rules import ARTIFACT_PROGRAM

keeps working and no caller has to know which module owns a name.

IMPORT ORDER IS THE DEPENDENCY ORDER:

    artifacts   -> identity, referenced by everything
    config      -> env keys, application, libraries, programs
    connection  -> hosts, URL, headers
    pipeline    -> workspace, steps, console templates
    messages    -> narrative, diagnostics, errors, warnings

Add a new constant to the module that owns its concern, never here.
"""

from __future__ import annotations

from zowe.zowe_rules_artifacts import *  # noqa: F401,F403
from zowe.zowe_rules_config import *  # noqa: F401,F403
from zowe.zowe_rules_connection import *  # noqa: F401,F403
from zowe.zowe_rules_pipeline import *  # noqa: F401,F403
from zowe.zowe_rules_messages import *  # noqa: F401,F403