# LOCATION: rules/sql_generation_rules.py
# ACTION: REPLACE ENTIRE FILE (adds the date sentinel constant)

"""
SQL generation constant tuples.

Constants only. No regex, no runtime logic.
"""

SELECT_EXCLUDE_PREFIXES = (
    "TS_CREATE",
    "TS_UPDATE",
    "ID_USERID",
    "NR_USERID",
)

FALLBACK_KEY_PREFIXES = (
    "CT_",
    "NR_",
    "NS_",
    "CO_",
)

DATE_COLUMN_PREFIXES = (
    "DA_",
    "DT_",
)

# DB2 low-date sentinel used when a source date is ZEROES or SPACES.
# Manual standard moves the numeric 00010101 (0001-01-01) into DA-CCYYMMDD
# instead of moving SPACES to the target date field.
DB2_DATE_NULL_SENTINEL = "00010101"

# Fields owned by the shared DB2 date conversion block. These are the
# OUTPUT of a conversion, never a valid INPUT. Feeding DA-DD-MM-CCYY
# (10 bytes) back into DA-CCYYMMDD (8 bytes) truncates and destroys
# the date. See CHK-18.
DATE_STAGING_FIELDS = (
    "DA-CCYYMMDD",
    "DA-CCYYMMDD-R",
    "DA-DD-MM-CCYY",
)
