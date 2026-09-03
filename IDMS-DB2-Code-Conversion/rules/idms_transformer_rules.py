from __future__ import annotations

# IDMS statement transformer rule constants. Constants only.
# No regex, no logic, no program/record/table names.

IDMS_TRANSFORMER_RULES = [
    "Convert only IDMS database statements and control statements.",
    "When removing executable PROCEDURE DIVISION IDMS code, add CONTINUE.",
    "Do not generate DB2 SQL for records without Sheet Mapping metadata.",
    "Do not add duplicate SQLCODE wrappers around generated SQL blocks.",
    "Do not hardcode program names, DB2 tables, columns, or host variables.",
]

# COBOL division name that permits executable conversion.
PROCEDURE_DIVISION_NAME = "PROCEDURE"

# Token used when an OBTAIN FIRST cursor keyword is detected.
OBTAIN_FIRST_KEYWORD = "FIRST"

# Replacement condition for IDMS end-of-set / record-not-found tokens.
SQLCODE_END_TOKEN_REPLACEMENT = "SQLCODE = 100"

# Generated CONTINUE line for emptied blocks.
CONTINUE_STATEMENT = "CONTINUE."

# SQLCODE=100 guard block scaffolding (ON DB-REC-NOT-FOUND).
SQLCODE_100_IF_OPEN = "IF SQLCODE = 100"
SQLCODE_100_IF_CLOSE = "END-IF."
SQLCODE_100_CONTINUE_BODY = "   CONTINUE"