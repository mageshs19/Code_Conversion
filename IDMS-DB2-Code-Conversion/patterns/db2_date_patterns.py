# LOCATION: patterns/db2_date_patterns.py
# ACTION: REPLACE ENTIRE FILE

"""DB2 date comparison regex patterns.

These patterns support conservative DB2 date realignment before comparing
DB2 date host fields with COBOL numeric date fields.

CORRECTION 1 - the host had to be the first token after IF
-----------------------------------------------------------
DB2_DATE_COMPARISON_PATTERN was anchored as

    ^\\s*IF\\s+(?:DA|DT)-...

so it matched only a bare single-operand IF. A parenthesised or compound
condition such as

    IF (DA-CPTAFS-479BFAS OF DCLDZBFASTV < DA-ARCH-YMD
       AND DA-CPTAFS-479BFAS OF DCLDZBFASTV NOT = '00000000') OR

never matched, the detector returned an empty field list, and the whole
pass was skipped in silence.

CORRECTION 2 - a business field name was hardcoded in patterns/
----------------------------------------------------------------
The old condition group was

    (?P<condition>.+\\bPARMDATE\\b.*)

PARMDATE is a host variable belonging to ONE program. rules/authority_rules
forbids hardcoding host variables anywhere, and any program comparing a
DATE host against a differently named field was silently skipped. The
comparison operand is no longer named; a DATE host is now recognised by
its DCLGEN-qualified shape alone.

CORRECTION 3 - multi-line conditions
-------------------------------------
Matching is performed against an ASSEMBLED logical condition, not a single
physical line. Db2DateConditionAssembler owns the assembly.

Regex only. No rules, no constants, no program / record / table / DCLGEN /
host variable names.
"""

from __future__ import annotations

import re

#
# Structure
#
WORKING_STORAGE_SECTION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?WORKING-STORAGE\s+SECTION\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)

LINKAGE_SECTION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?LINKAGE\s+SECTION\.\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)

PROCEDURE_DIVISION_PATTERN = re.compile(
    r"^\s*(?:\d{6}\s+)?PROCEDURE\s+DIVISION\b.*\.?\s*(?:\d{8})?\s*$",
    flags=re.IGNORECASE,
)

#
# Condition span detection
#
# Any line that opens a condition. The operands are NOT constrained here;
# the assembler decides how far the condition runs.
IF_START_PATTERN = re.compile(
    r"^(?P<indent>\s*)IF\b(?P<rest>.*)$",
    flags=re.IGNORECASE,
)

# A line that plainly continues a condition rather than starting a
# statement: it opens with a boolean operator or a parenthesis.
CONDITION_CONTINUATION_PATTERN = re.compile(
    r"^\s*(?:(?:AND|OR|NOT)\b|\()",
    flags=re.IGNORECASE,
)

# A line that plainly ends a condition by starting a statement.
STATEMENT_START_PATTERN = re.compile(
    r"^\s*(?:ACCEPT|ADD|CALL|CANCEL|CLOSE|COMPUTE|CONTINUE|DELETE|DISPLAY"
    r"|DIVIDE|ELSE|END-IF|EVALUATE|EXEC|EXIT|GO|GOBACK|IF|INITIALIZE"
    r"|INSPECT|MERGE|MOVE|MULTIPLY|OPEN|PERFORM|READ|RELEASE|RETURN"
    r"|REWRITE|SEARCH|SET|SORT|START|STOP|STRING|SUBTRACT|UNSTRING"
    r"|WRITE)\b",
    flags=re.IGNORECASE,
)

# A condition line ending on a dangling boolean operator.
TRAILING_BOOLEAN_PATTERN = re.compile(
    r"\b(?:AND|OR|NOT)\s*$",
    flags=re.IGNORECASE,
)

#
# DATE host operands
#
# A DCLGEN-qualified DB2 date host, anywhere in a condition:
#     DA-CPTAFS-479BFAS OF DCLDZBFASTV
#
# finditer over the ASSEMBLED condition yields every operand, so a
# compound condition reports all of them instead of only the first.
DB2_DATE_HOST_OPERAND_PATTERN = re.compile(
    r"\b(?P<field>(?:DA|DT)-[A-Z0-9-]+)"
    r"\s+OF\s+"
    r"(?P<group>DCL[A-Z0-9-]+)\b",
    flags=re.IGNORECASE,
)

# The same operand written in SQL host form, which must NEVER be rewritten.
SQL_HOST_OPERAND_PATTERN = re.compile(
    r":\s*(?:DCL[A-Z0-9-]+\.)?(?:DA|DT)-[A-Z0-9-]+",
    flags=re.IGNORECASE,
)

# A comparison operator, used to prove the operand is actually compared
# and not merely referenced inside a MOVE that happens to sit on the line.
COMPARISON_OPERATOR_PATTERN = re.compile(
    r"(?:<=|>=|<>|=|<|>|\bNOT\s+=|\bEQUAL\b|\bGREATER\b|\bLESS\b)",
    flags=re.IGNORECASE,
)

#
# Embedded SQL guard
#
EXEC_SQL_START_PATTERN = re.compile(
    r"^\s*EXEC\s+SQL\b",
    flags=re.IGNORECASE,
)

END_EXEC_PATTERN = re.compile(
    r"\bEND-EXEC\b",
    flags=re.IGNORECASE,
)

#
# Working storage
#
DATE_HELPER_FIELD_PATTERN = re.compile(
    r"\bHELP-(?:DA|DT)-[A-Z0-9-]+\b",
    flags=re.IGNORECASE,
)

DATE_WORKING_STORAGE_MARKER_PATTERN = re.compile(
    r"DB2 DATE (?:COMPARISON|CONVERSION) WORKING STORAGE",
    flags=re.IGNORECASE,
)

DB2_SHARED_DATE_HELPER_USAGE_PATTERN = re.compile(
    r"\b(?:DA-CCYYMMDD-R|DA-CCYYMMDD|DA-DD-MM-CCYY)\b",
    flags=re.IGNORECASE,
)

DB2_DATE_WORKING_STORAGE_BASE_PATTERN = re.compile(
    r"\b(?:01\s+WS-DATUMVELDEN|DA-CCYYMMDD|DA-DD-MM-CCYY)\b",
    flags=re.IGNORECASE,
)

#
# DEPRECATED
#
# Retained only so an unmigrated import does not raise. It matches the
# narrow single-operand shape and must not be used for detection.
DB2_DATE_COMPARISON_PATTERN = re.compile(
    r"^(?P<indent>\s*)IF\s+"
    r"(?P<field>(?:DA|DT)-[A-Z0-9-]+)"
    r"\s+OF\s+"
    r"(?P<group>DCL[A-Z0-9-]+)"
    r"\s+"
    r"(?P<condition>.+)$",
    flags=re.IGNORECASE,
)

__all__ = [
    "WORKING_STORAGE_SECTION_PATTERN",
    "LINKAGE_SECTION_PATTERN",
    "PROCEDURE_DIVISION_PATTERN",
    "IF_START_PATTERN",
    "CONDITION_CONTINUATION_PATTERN",
    "STATEMENT_START_PATTERN",
    "TRAILING_BOOLEAN_PATTERN",
    "DB2_DATE_HOST_OPERAND_PATTERN",
    "SQL_HOST_OPERAND_PATTERN",
    "COMPARISON_OPERATOR_PATTERN",
    "EXEC_SQL_START_PATTERN",
    "END_EXEC_PATTERN",
    "DATE_HELPER_FIELD_PATTERN",
    "DATE_WORKING_STORAGE_MARKER_PATTERN",
    "DB2_SHARED_DATE_HELPER_USAGE_PATTERN",
    "DB2_DATE_WORKING_STORAGE_BASE_PATTERN",
    "DB2_DATE_COMPARISON_PATTERN",
]