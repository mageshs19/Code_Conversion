# LOCATION: zowe/zowe_rules_messages.py
# ACTION: CREATE NEW FILE
"""Narrative, diagnostics, log formats, errors and warnings.

Text only. Every message the package can emit lives here, so wording
never drifts between modules.
"""

from __future__ import annotations

ZOWE_RULES = [
    "Zowe is an input SOURCE only. It never parses or converts COBOL.",
    "One Program folder. Retrieval and Update are not separated.",
    "Each artifact owns an ORDERED library list, searched until found.",
    "The selected program array decides what is fetched and converted.",
    "DCLGEN members are derived from the IDMS record name, not guessed.",
    "Subschema may live on a different environment, TSO and CPU.",
    "Mapping Sheet is a local Excel or CSV artifact and is never fetched.",
    "Credentials and library names come from .env, never from source code.",
    "A missing optional member is a warning, never a blocker.",
]

# ---- Diagnostics ----
DIAG_START_FETCH = "START ZOWE INPUT FETCH"
DIAG_END_FETCH = "END ZOWE INPUT FETCH"
DIAG_APPLICATION_TEMPLATE = "Application code: {application}"
DIAG_PROGRAM_LIST_TEMPLATE = "Programs selected: {count} ({names})"
DIAG_LIBRARY_ORDER_TEMPLATE = "{label} library search order: {libraries}"
DIAG_CONNECTION_TEMPLATE = "{label} connection: {host}:{port} as {user}"
DIAG_FOUND_TEMPLATE = "{label} {member}: found in {dataset} -> {path}"
DIAG_NOT_FOUND_TEMPLATE = (
    "{label} {member}: NOT FOUND in any library. Searched: {libraries}"
)
DIAG_DERIVED_DCLGEN_TEMPLATE = "IDMS record {record} -> DCLGEN member {member}"
DIAG_SUBSCHEMA_DETECTED_TEMPLATE = "Subschema detected in {program}: {subschema}"
DIAG_DEPENDENCIES_TEMPLATE = (
    "{program}: {copybooks} copybook(s), {records} record(s), subschema {subschema}"
)
DIAG_UPLOAD_TEMPLATE = "Uploaded {path} -> {dataset}({member})"
DIAG_VERIFIED_TEMPLATE = "Verified {dataset}({member}): {size} byte(s)"
DIAG_MAPPING_LOCAL = (
    "Mapping Sheet is a local artifact. Keep the Excel or CSV file in the "
    "workspace Mapping Sheet folder. Zowe does not fetch it."
)
DIAG_TOTAL_TEMPLATE = "Zowe fetched {count} file(s) across {artifacts} artifact(s)."

# ---- Log formats (printf-style) ----
LOG_CONNECTION = "%s connection: %s:%s"
LOG_DOWNLOAD = "Zowe download %s(%s): HTTP %s"
LOG_UPLOAD = "Zowe upload %s(%s): HTTP %s"
LOG_MEMBER_COUNT = "%s member count: %s"

# ---- Errors ----
ZOWE_ERROR_MESSAGES = {
    "missing_host": (
        "No host configured for {label}. Set ZOWE_{artifact}_HOST in the .env "
        "file, or set the shared ZOWE_HOST."
    ),
    "missing_credentials": (
        "No credentials configured for {label}. Set ZOWE_{artifact}_USER and "
        "ZOWE_{artifact}_PASSWORD in the .env file, or set the shared "
        "ZOWE_USER and ZOWE_PASSWORD."
    ),
    "no_libraries": (
        "{label} has no libraries configured. Set ZOWE_{artifact}_LIBRARIES "
        "in the .env file."
    ),
    "no_programs": (
        "No programs selected. Set ZOWE_PROGRAMS or list them in {file}."
    ),
    "program_not_found": (
        "Program {member} was not found in any configured library. "
        "Searched: {libraries}"
    ),
    "invalid_dataset": "A valid library name is required, not: {dataset}",
    "member_path_not_allowed": (
        "A library name is required, not a member path: {dataset}"
    ),
    "no_members": "No members found in dataset: {dataset}",
    "read_only": "Output library is marked read-only. Upload refused: {dataset}",
    "verify_mismatch": (
        "Verification failed for {dataset}({member}). Uploaded {sent} byte(s), "
        "retrieved {received} byte(s)."
    ),
    "output_not_configured": (
        "No output dataset configured. Set ZOWE_OUTPUT_DATASET in the .env file."
    ),
    "bare_key_reference": (
        "{key} is set to the literal text '{value}', which looks like another "
        "configuration key. To inherit the shared value, remove the line or "
        "leave it blank. To reference it explicitly, wrap it in dollar-braces."
    ),
    "unresolved_reference": (
        "{key} references {missing}, which is not set. Define {missing} in the "
        ".env file or remove the reference."
    ),
    "circular_reference": (
        "{key} could not be resolved after {depth} substitutions. Check for a "
        "circular reference in the .env file."
    ),
}

# ---- Warnings - never a blocker ----
ZOWE_WARNING_MESSAGES = {
    "member_not_found": (
        "{label} member {member} was not found. Searched: {libraries}. "
        "Conversion will continue and report the gap."
    ),
    "subschema_not_configured": (
        "No subschema library configured. Logical record access, if any, will "
        "be reported for manual review."
    ),
    "subschema_not_detected": (
        "{program} declares no subschema. Logical record metadata will be "
        "skipped for this program."
    ),
    "tls_unverified": (
        "TLS certificate verification is disabled for {label} ({host}). Set "
        "ZOWE_{artifact}_VERIFY_TLS=true once the certificate is trusted."
    ),
}