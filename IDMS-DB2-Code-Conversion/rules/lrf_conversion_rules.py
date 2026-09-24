# LOCATION: rules/lrf_conversion_rules.py
# ACTION: CREATE NEW FILE
"""LRF -> classic IDMS expansion rules.

Constants only. No regex, no runtime logic, no program / record / table /
set / cursor / host variable names.

WHY THIS EXISTS

The converter already knows how to turn

    OBTAIN FIRST <record> WITHIN <set>.

into a DB2 cursor with OPEN / FETCH / CLOSE paragraphs, join predicates,
QUERYNO and an EOC flag.

It does NOT know the Logical Record Facility form

    OBTAIN FIRST <logical-record> WHERE <path-keyword>.

Teaching every downstream generator about logical records would duplicate
that machinery. Instead, a single pre-pass rewrites the LRF form into the
classic form using the parsed subschema path, and every existing rule
applies unchanged.
"""

from __future__ import annotations

# ---------------------------------------------------------------- master
ENABLE_LRF_PATH_EXPANSION = True

# Expand only when the driving element record resolves to a DB2 table.
REQUIRE_MAPPED_DRIVING_RECORD = True

# ------------------------------------------------------- expanded syntax
OBTAIN_FIRST_TEMPLATE = "OBTAIN FIRST {record} WITHIN {within}"
OBTAIN_NEXT_TEMPLATE = "OBTAIN NEXT {record} WITHIN {within}"
FIND_FIRST_TEMPLATE = "FIND FIRST {record} WITHIN {within}"
STATEMENT_TERMINATOR = "."

# IDMS token the converter already maps to "SQLCODE = 100".
END_OF_SET_TOKEN = "DB-END-OF-SET"
RECORD_NOT_FOUND_TOKEN = "DB-REC-NOT-FOUND"

# IDMS path status codes that mean "no more rows" / "not found".
STATUS_END_OF_SET = "0307"
STATUS_NOT_FOUND = "0326"
STATUS_SET_EMPTY = "1601"

# --------------------------------------------------------- LR-CTRL field
# Declared by COPY IDMS SUBSCHEMA-LR-CTRL. Never emitted into DB2 output.
LR_STATUS_FIELD = "LR-STATUS"
LR_QUALIFIER = "OF LR"

# ------------------------------------------------------------- comments
COMMENT_PREFIX = "*DB2: "
EXPANDED_OBTAIN_TEMPLATE = (
    "*DB2: Expanded LRF {mode} {lr} WHERE {keyword} "
    "-> {record} WITHIN {within}."
)
EXPANDED_PARENT_TEMPLATE = (
    "*DB2: LRF path {keyword} parent access on {record}."
)
SKIPPED_NO_PATH_TEMPLATE = (
    "*DB2-KEEP: LRF path keyword {keyword} not found in the supplied "
    "subschema - expand this access manually."
)
SKIPPED_NO_RECORD_TEMPLATE = (
    "*DB2-KEEP: LRF path {keyword} has no resolvable driving record "
    "- expand this access manually."
)
SKIPPED_UNMAPPED_TEMPLATE = (
    "*DB2-KEEP: LRF driving record {record} has no Sheet Mapping entry "
    "- expand this access manually."
)
REMOVED_LR_STATUS_TEMPLATE = (
    "*DB2: Replaced LR-STATUS test with the cursor end-of-cursor test."
)

# ----------------------------------------------------------- diagnostics
LRF_EXPANSION_MESSAGES = {
    "expanded": (
        "LRF expansion: {mode} {lr} WHERE {keyword} expanded to "
        "{record} WITHIN {within}."
    ),
    "parent_emitted": (
        "LRF expansion: emitted parent access {record} WITHIN {within} "
        "for keyword {keyword}."
    ),
    "status_rewritten": (
        "LRF expansion: rewrote {count} LR-STATUS condition(s) to the "
        "IDMS end-of-set token."
    ),
    "qualifier_stripped": (
        "LRF expansion: stripped {count} 'OF LR' qualifier(s)."
    ),
    "keyword_not_found": (
        "LRF expansion: keyword {keyword} is not declared in the supplied "
        "subschema; the statement was left for manual review."
    ),
    "record_unmapped": (
        "LRF expansion: driving record {record} for keyword {keyword} has "
        "no Sheet Mapping entry; the statement was left for manual review."
    ),
    "no_logical_records": (
        "LRF expansion: no logical record metadata supplied; LRF statements "
        "are left unchanged."
    ),
    "summary": (
        "LRF expansion: expanded {expanded} statement(s), skipped {skipped}."
    ),
}