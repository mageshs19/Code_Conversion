# LOCATION: zowe/zowe_rules_artifacts.py
# ACTION: CREATE NEW FILE
"""Artifact identity: keys, labels, extensions, landing folders.

Constants only. Declared FIRST because every other rules module and
dictionary references these names.
"""

from __future__ import annotations

ARTIFACT_PROGRAM = "PROGRAM"
ARTIFACT_COPYBOOK = "COPYBOOK"
ARTIFACT_DCLGEN = "DCLGEN"
ARTIFACT_SUBSCHEMA = "SUBSCHEMA"
ARTIFACT_OUTPUT = "OUTPUT"

ZOWE_ARTIFACT_KEYS = (
    ARTIFACT_PROGRAM,
    ARTIFACT_COPYBOOK,
    ARTIFACT_DCLGEN,
    ARTIFACT_SUBSCHEMA,
)

ARTIFACT_LABELS = {
    ARTIFACT_PROGRAM: "Program",
    ARTIFACT_COPYBOOK: "Copybook",
    ARTIFACT_DCLGEN: "DCLGEN",
    ARTIFACT_SUBSCHEMA: "Subschema",
    ARTIFACT_OUTPUT: "Output",
}

# Program, Copybook and DCLGEN must resolve. Subschema stays optional.
MANDATORY_ARTIFACTS = (ARTIFACT_PROGRAM, ARTIFACT_COPYBOOK, ARTIFACT_DCLGEN)

OPTIONAL_WARNING_KEYS = {ARTIFACT_SUBSCHEMA: "subschema_not_configured"}

ARTIFACT_EXTENSIONS = {
    ARTIFACT_PROGRAM: ".cbl",
    ARTIFACT_COPYBOOK: ".cpy",
    ARTIFACT_DCLGEN: ".txt",
    ARTIFACT_SUBSCHEMA: ".txt",
    ARTIFACT_OUTPUT: ".cbl",
}

# Forward slashes only. pathlib translates them on Windows; a backslash
# would become part of the folder NAME on Linux and macOS.
DEFAULT_LANDING_SUBFOLDERS = {
    ARTIFACT_PROGRAM: "Program",
    ARTIFACT_COPYBOOK: "Copybook",
    ARTIFACT_DCLGEN: "DCLGen",
    ARTIFACT_SUBSCHEMA: "Subschema",
    ARTIFACT_OUTPUT: "Output",
}