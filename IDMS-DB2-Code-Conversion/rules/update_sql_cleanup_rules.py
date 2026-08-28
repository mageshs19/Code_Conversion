# LOCATION: rules/update_sql_cleanup_rules.py
# ACTION: REPLACE ENTIRE FILE
import re
"""
Update-program SQL cleanup constant tuples.

Constants only. No regex, no runtime logic.
"""

PROTECTED_BARE_TARGET_PREFIXES = (
    "WS-",
    "SW-",
    "WK-",
    "W-",
    "UIT-",
    "OUT-",
    "ES-",
    "SQL",
    "DCL",
    "ERROR-",
    "USER",
    "CS-",
    "TS-",
    "HR-",
    "HELP-",
    "PROGRAM-",
)

UPDATE_AUDIT_PREFIXES = (
    "TS_UPDATE",
    "ID_USERID",
    "NR_USERID",
    "ID_USER",
    "NR_USER",
)

INSERT_ONLY_AUDIT_PREFIXES = (
    "TS_CREATE",
)

IDENTITY_KEY_PREFIXES = (
    "NS_ID",
    "NR_ID",
    "ID_",
    "CO_ID",
    "NR_IS",
)

# --- Category E: manual-standard SQL block ---

# QUERYNO value appended to generated INSERT/UPDATE/DELETE statements
# (manual standard) so DB2 EXPLAIN can identify the generated statement.
UPDATE_QUERYNO = "442"

# When True, generated SQL uses EVALUATE SQLCODE (manual standard) instead
# of the older IF SQLCODE NOT = 0 form.
USE_EVALUATE_SQLCODE = True

# LOCATION: composers/update_sql_cleanup/update_sql_cleanup_patterns.py
# ACTION: APPEND these patterns to the existing file (add at the end)

# --- SQLCODE handling block detection (IF and EVALUATE forms) ---

SQLCODE_EVALUATE_PATTERN = re.compile(
    r"^\s*EVALUATE\s+SQLCODE\b",
    flags=re.IGNORECASE,
)

END_EVALUATE_PATTERN = re.compile(
    r"^\s*END-EVALUATE\.?\s*$",
    flags=re.IGNORECASE,
)

# A lone period line that closes an EVALUATE block (COBOL scope terminator).
LONE_PERIOD_PATTERN = re.compile(
    r"^\s*\.\s*$",
    flags=re.IGNORECASE,
)