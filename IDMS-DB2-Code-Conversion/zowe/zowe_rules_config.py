# LOCATION: zowe/zowe_rules_config.py
# ACTION: CREATE NEW FILE
"""Configuration vocabulary: env keys, application, libraries, programs.

Constants only. No artifact identity, no connection defaults.
"""

from __future__ import annotations

# ---- Environment variable name templates ----
ARTIFACT_KEY_TEMPLATE = "ZOWE_{artifact}_{name}"
SHARED_KEY_TEMPLATE = "ZOWE_{name}"

NAME_HOST = "HOST"
NAME_PORT = "PORT"
NAME_USER = "USER"
NAME_PASSWORD = "PASSWORD"
NAME_VERIFY_TLS = "VERIFY_TLS"
NAME_TIMEOUT = "TIMEOUT_SECONDS"
NAME_DATASET = "DATASET"
NAME_LIBRARIES = "LIBRARIES"
NAME_MEMBER = "MEMBER"
NAME_LANDING = "LANDING"
NAME_READ_ONLY = "READ_ONLY"
NAME_APPLICATION = "APPLICATION"
NAME_PROGRAMS = "PROGRAMS"
NAME_PROGRAM_LIST_FILE = "PROGRAM_LIST_FILE"

WORKSPACE_ROOT_KEY = "ZOWE_WORKSPACE_ROOT"
WORKSPACE_DIR_NAME = "workspace"

# ---- Input source selection ----
INPUT_SOURCE_ENV_KEY = "INPUT_SOURCE"
INPUT_SOURCE_LOCAL = "LOCAL"
INPUT_SOURCE_UPLOAD = "UPLOAD"
INPUT_SOURCE_ZOWE = "ZOWE"
SUPPORTED_INPUT_SOURCES = (
    INPUT_SOURCE_LOCAL,
    INPUT_SOURCE_UPLOAD,
    INPUT_SOURCE_ZOWE,
)

# ---- Application code and library lists ----
APPLICATION_PLACEHOLDER = "{XY}"
DEFAULT_APPLICATION = "VM"
LIBRARY_SEPARATOR = ","

# ---- Program selection ----
DEFAULT_PROGRAM_LIST_FILE = "program_list.txt"
PROGRAM_LIST_COMMENT = "#"

# ---- DCLGEN derivation: DZ + last 4 of the IDMS record + TV ----
DCLGEN_PREFIX = "DZ"
DCLGEN_SUFFIX = "TV"
DCLGEN_RECORD_TAIL_LENGTH = 4
DCLGEN_MEMBER_TEMPLATE = "{prefix}{tail}{suffix}"

# ---- Value reference resolution ----
# A value may reference another key. Depth is capped so a circular chain
# fails loudly instead of hanging.
ENV_REFERENCE_MAX_DEPTH = 5

# Names whose value must never reach a diagnostic or a console line.
SENSITIVE_NAMES = (NAME_PASSWORD,)
MASKED_VALUE = "********"
SEQUENCE_AREA_WIDTH = 6      # columns 1-6
INDICATOR_COLUMN = 6         # zero-based index of column 7
BODY_START_COLUMN = 7        # zero-based index of column 8
BODY_END_COLUMN = 72         # columns 8-72
COMMENT_INDICATORS = ("*", "/")

# LOCATION: zowe/zowe_rules_config.py
# ACTION: APPEND at the end of the file

# ---- Subschema DDL vocabulary ----
# IDMS subschema clause keywords. A line beginning with any of these
# starts a NEW clause and therefore ends the ELEMENTS name list.
# These are language keywords, never business names.
SUBSCHEMA_CLAUSE_KEYWORDS = (
    "ADD",
    "MODIFY",
    "DELETE",
    "COMMENTS",
    "COMMENT",
    "DESCRIPTION",
    "PATH-GROUP",
    "SELECT",
    "WITHIN",
    "PUBLIC",
    "SHARE",
    "REGISTERED",
    "END",
)

# Tokens that may appear inside the ELEMENTS clause itself.
SUBSCHEMA_ELEMENT_NOISE = ("ELEMENTS", "ELEMENT", "ARE", "IS", "NAME")

# Minimum element-name length. Shorter tokens are separators or noise.
ELEMENT_NAME_MIN_LENGTH = 4

# Optional filter. Set ZOWE_RECORD_PREFIX in .env to accept only records
# of one application, for example VM. Blank accepts every name.
NAME_RECORD_PREFIX = "RECORD_PREFIX"