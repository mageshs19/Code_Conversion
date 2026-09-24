# LOCATION: rules/record_materialisation_rules.py

from __future__ import annotations

# =====================================================================
# Master switch
# =====================================================================
ENFORCE_RECORD_MATERIALISATION = True

# A record is materialised only when EVERY COBOL field in the Sheet
# Mapping resolves to a DCLGEN host variable. One unresolved field means
# the written record would carry a silent hole, so the whole conversion
# is refused and the original move is left for manual review.
REQUIRE_COMPLETE_FIELD_COVERAGE = True

# The materialised layout must occupy exactly the same number of bytes as
# the PIC it replaces. A mismatch shifts every field after it in a
# fixed-length record, which is silent data corruption.
ENFORCE_LENGTH_MATCH = True

# Byte tolerance. 0 = exact. Raise only with COBOL-team agreement.
LENGTH_TOLERANCE = 0

# =====================================================================
# Layout generation
# =====================================================================
LAYOUT_BASE_INDENT = "    "          # column 12, Area B
LAYOUT_LEVEL_STEP = "    "           # one nesting step
LAYOUT_NAME_WIDTH = 24

GROUP_ITEM_TEMPLATE = "{level}  {name}."
ELEMENTARY_ITEM_TEMPLATE = "{level}  {name:<{width}} {picture}"
REDEFINES_TEMPLATE = "{level}  {name} REDEFINES {base}{picture}"

LAYOUT_MARKER_TEMPLATE = "DB2 MATERIALISED IDMS RECORD {record}"

# A mapping row with no PIC clause is a group item.
GROUP_PICTURE_TOKENS = ("GROUP", "")

# =====================================================================
# Move generation
# =====================================================================
MOVE_MARKER_TEMPLATE = (
    "*DB2: Materialised {record} from {group} - {count} field move(s)."
)
MOVE_TEMPLATE = "MOVE {host} TO"
MOVE_TARGET_TEMPLATE = "     {field} OF {record}"
MOVE_INDENT = "    "

EMIT_DATE_CONVERSION = True

DATE_LOW_VALUE_LITERAL = "01.01.0001"
DATE_HIGH_VALUE_LITERAL = "31.12.9999"
DATE_HIGH_NUMERIC_LITERAL = "99999999"

DATE_CONVERSION_LINE_TEMPLATES = [
    "MOVE {host} TO DA-DD-MM-CCYY",
    "EVALUATE TRUE",
    "  WHEN DA-DD-MM-CCYY = '{low_value}'",
    "       MOVE ZEROES TO DA-CCYYMMDD-R",
    "  WHEN DA-DD-MM-CCYY = '{high_value}'",
    "       MOVE '{high_numeric}' TO DA-CCYYMMDD-R",
    "  WHEN OTHER",
    "       MOVE CCYY OF DA-DD-MM-CCYY TO CCYY OF DA-CCYYMMDD-R",
    "       MOVE MM   OF DA-DD-MM-CCYY TO MM   OF DA-CCYYMMDD-R",
    "       MOVE DD   OF DA-DD-MM-CCYY TO DD   OF DA-CCYYMMDD-R",
    "END-EVALUATE",
    "MOVE DA-CCYYMMDD-R TO {field} OF {record}",
]

# DB2 types that need the conversion block. TIMESTAMP and TIME receive a
# formatted timestamp, never a DD.MM.CCYY date.
DATE_DB2_TYPE_PREFIX = "DATE"
NON_DATE_DB2_TYPE_PREFIXES = ("TIMESTAMP", "TIME")

# =====================================================================
# Diagnostics
# =====================================================================
RECORD_MATERIALISATION_MESSAGES = {
    "materialised": (
        "Record materialisation: expanded {target} into the {record} "
        "layout ({fields} field(s), {bytes} bytes) and generated "
        "{moves} move statement(s)."
    ),
    "layout_inserted": (
        "Record materialisation: inserted the {record} layout under "
        "{target}."
    ),
    "skipped_no_mapping": (
        "Record materialisation: {record} has no Sheet Mapping rows; the "
        "whole-record move was left for manual review."
    ),
    "skipped_incomplete": (
        "Record materialisation: {record} has {missing} field(s) with no "
        "DCLGEN host variable ({names}); the whole-record move was left "
        "for manual review."
    ),
    "skipped_length": (
        "Record materialisation: {record} layout is {actual} bytes but "
        "{target} declares {expected}; refused rather than shift the "
        "record."
    ),
    "skipped_no_target": (
        "Record materialisation: target field {target} was not found in "
        "the DATA DIVISION."
    ),
    "skipped_no_group": (
        "Record materialisation: no DCLGEN group resolved for {record}."
    ),
}


# ---- A: length ----
ALLOW_LAYOUT_SHORTER_THAN_TARGET = True
EMIT_REMAINDER_FILLER = True
REMAINDER_FILLER_NAME = "FILLER"
REMAINDER_FILLER_PICTURE_TEMPLATE = "PIC X({bytes})"

# ---- C: sentinels ----
# Field names that are storage placeholders, never data carriers.
FILLER_FIELD_NAMES = ("FILLER",)

# Values a mapping sheet puts in the DB2 column cell meaning "no column".
# Compared upper-cased after strip.
NON_COLUMN_SENTINELS = ("", "FILLER", "N/A", "NA", "-", "NONE")

# ---- E: scan ----
# Runaway guard on the number of whole-record MOVEs rewritten per program.
MAX_RECORD_MOVES = 64

# Suffixes identifying a work/staging field rather than an IDMS record
# (for example a LINKAGE SECTION date field). Suffix driven, so no record
# name is hardcoded.
NON_RECORD_NAME_SUFFIXES = ("-LS", "-WS", "-R", "-X")

# ---- level rebasing ----
# The record group sits one level below the target field it replaces.
RECORD_GROUP_LEVEL_STEP = 1
MIN_LEVEL = 1
MAX_LEVEL = 49

# ---- new messages ----
RECORD_MATERIALISATION_MESSAGES.update({
    "remainder_filler": (
        "Record materialisation: {record} occupies {actual} of {expected} "
        "byte(s) in {target}; {remainder} trailing byte(s) declared as "
        "FILLER so the record length is unchanged."
    ),
    "skipped_too_long": (
        "Record materialisation: {record} layout is {actual} bytes but "
        "{target} declares only {expected}; refused rather than shift the "
        "record."
    ),
    "skipped_not_a_record": (
        "Record materialisation: {record} is a work field, not a mapped "
        "IDMS record; the move was left unchanged."
    ),
    "declared_only": (
        "Record materialisation: {record} produced {fields} declared "
        "field(s) but 0 movable field(s); the layout was emitted and no "
        "data is populated. Check the Sheet Mapping DB2 column cells."
    ),
    "no_moves": (
        "Record materialisation: no whole-record MOVE statement was found "
        "in the PROCEDURE DIVISION; nothing to materialise."
    ),
    "scan_summary": (
        "Record materialisation: {examined} whole-record move(s) examined, "
        "{applied} materialised, {refused} left for manual review."
    ),
    "composer_absent": (
        "Record materialisation: the composer is not wired into this "
        "build; every whole-record MOVE was left unchanged."
    ),
})


# ---- Fixed-format geometry (cols 8-72) ----
LAYOUT_BODY_WIDTH = 65

# Area A is columns 8-11; levels 02-49 must start at column 12 or later.
# 4 spaces from column 8 lands the level number at column 12.
LAYOUT_BASE_INDENT = "    "

# 2 spaces per nesting level, not 4. VMBFAS nests 6 deep; a 4-space step
# put a level-11 entry at column 29 and the picture past column 72.
LAYOUT_LEVEL_STEP = "  "

# Hard ceiling on nesting indent, so no depth can overflow the body.
LAYOUT_MAX_INDENT_DEPTH = 6

# Column at which the PICTURE starts, relative to the start of the body.
# Reduced automatically when the entry would not fit.
LAYOUT_NAME_WIDTH = 24
LAYOUT_MIN_NAME_GAP = 1

# ---- Entry templates ----
# The trailing period is added by the generator, never by the template.
GROUP_ITEM_TEMPLATE = "{level}  {name}."
ELEMENTARY_ITEM_TEMPLATE = "{level}  {name:<{width}}{picture}"

# DEFECT: the old template had no separator between {base} and {picture}.
REDEFINES_TEMPLATE = "{level}  {name} REDEFINES {base}{gap}{picture}"

LAYOUT_MARKER_TEMPLATE = "DB2 MATERIALISED IDMS RECORD {record}"

MOVE_TEMPLATE = "MOVE {host} TO"
MOVE_TARGET_TEMPLATE = "     {field} OF {record}"


# ---- REDEFINES wrapping ----
WRAP_REDEFINES_ENTRY = True

# A single-line REDEFINES longer than this is split. 58 leaves headroom
# inside the 65-column body for the period and the sequence gap.
REDEFINES_INLINE_LIMIT = 58

# Head line carries level, name and the REDEFINES clause.
REDEFINES_HEAD_TEMPLATE = "{level}  {name}{gap}REDEFINES {base}"

# The picture continues on the next line, aligned under the data-name.
REDEFINES_CONTINUATION_GAP = 4

# ---- MOVE continuation ----
# Applied by RecordMoveGenerator in code. Five spaces places the target
# under the source, matching the manual reference.
MOVE_CONTINUATION_INDENT = "     "

# A MOVE short enough to fit on one line is emitted on one line.
MOVE_INLINE_LIMIT = 56

# ---- Diagnostic for a target with no readable PIC ----
RECORD_MATERIALISATION_MESSAGES.update({
    "no_declared_length": (
        "Record materialisation: {target} carries no readable PIC "
        "length, so the {record} remainder FILLER could not be sized. "
        "The record may be shorter than {target} declares - verify the "
        "written record length."
    ),
})

RECORD_MATERIALISATION_MESSAGES.update({
    "refusal_summary": (
        "Record materialisation: {count} record(s) refused - {details}. "
        "The whole-record MOVE was left in place and will be commented "
        "by the structural safety pass."
    ),
    "target_measured": (
        "Record materialisation: target {target} measured at {bytes} "
        "byte(s); {record} layout is {actual} byte(s)."
    ),
})

# Emit the per-target measurement on every attempt. It is two numbers
# and it makes a length refusal self-explanatory without a code read.
EMIT_TARGET_MEASUREMENT = True