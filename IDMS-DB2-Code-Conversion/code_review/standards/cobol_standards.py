"""Expected values. THIS FILE IS OWNED BY THE COBOL TEAM.

Constants only. No regex, no logic, no program names, no DB2 table names.
Change a value here and every check that reads it follows.
"""

from __future__ import annotations

# ---- CHK-01 line layout ----------------------------------------------
LINE_WIDTH = 80
BODY_FIRST_COLUMN = 8
BODY_LAST_COLUMN = 72
VALID_INDICATORS = (" ", "*", "/", "D", "-")
ENFORCE_SEQUENCE_START = False
LEFT_SEQUENCE_START = 10
RIGHT_SEQUENCE_START = 10000

# ---- CHK-02 DB2 infrastructure ---------------------------------------
REQUIRED_TOKENS = ("EXEC SQL", "SQLCA", "END-EXEC")
REQUIRED_LINES = (
    "EXEC SQL INCLUDE SQLCA END-EXEC.",
    "EXEC SQL INCLUDE SQLERRWS END-EXEC.",
)
SQL_LOCATION_FIELD = "SQL-LOCATION"
SQL_LOCATION_PICTURE = "PIC X(40) VALUE SPACES."
UNIQUE_MARKERS = (
    "DB2 SQLCA, SQL ERROR WORKING STORAGE, DCLGEN INCLUDES, AND CURSOR FLAGS",
    "DB2 CURSOR DECLARATIONS",
    "DB2 GENERATED CURSOR OPEN FETCH CLOSE PARAGRAPHS",
)
FORBIDDEN_MARKERS = (
    "TODO", "TODO-HOST-VARIABLE", "DB2 WARNING",
    "UNABLE TO DECLARE CURSOR", "NO FETCH HOST VARIABLES MAPPED",
)

# ---- CHK-03 residual IDMS --------------------------------------------
IDMS_EXECUTABLE_PREFIXES = (
    "OBTAIN", "STORE ", "MODIFY ", "ERASE ", "FIND CURRENT", "FIND FIRST",
    "BIND ", "READY ", "CONNECT ", "DISCONNECT ", "FINISH",
)
IDMS_DECLARATIVE_PREFIXES = (
    "IDMS-CONTROL SECTION", "PROTOCOL", "SCHEMA SECTION",
    "IDMS-RECORDS WITHIN", "COPY IDMS",
)
IDMS_TOKENS = ("IDMS-STATUS", "IDMS-ABORT", "DB-REC-NOT-FOUND", "DB-END-OF-SET")
IDMS_CLAUSES = ("USAGE-MODE IS UPDATE", "USAGE-MODE IS RETRIEVAL")

# ---- CHK-04 program header -------------------------------------------
COMPILER_OPTION_LINE = "CBL ARITH(EXTEND)"
NAME_PREFIX = "VM"
NAME_SOURCE_MARKER = "BD"
NAME_TARGET_MARKER = "DZ"
CS_PROGRAM_LEVELS = ("01", "77")

# ---- CHK-05 SQL error routing ----------------------------------------
SQL_ERROR_PARAGRAPH = "SQLERROR"
LEGACY_SQL_ERROR_PARAGRAPH = "SQL-ERROR"

# ---- CHK-06 Area A / Area B alignment --------------------------------
AREA_A_FIRST_COLUMN = 8
AREA_A_LAST_COLUMN = 11
AREA_B_FIRST_COLUMN = 12
AREA_A_MAX_INDENT = 3
AREA_B_MIN_INDENT = 4

DIVISION_NAMES = ("IDENTIFICATION", "ENVIRONMENT", "DATA", "PROCEDURE")
AREA_A_LEVEL_NUMBERS = ("01", "77")
AREA_B_LEVEL_NUMBERS = (
    "02", "03", "04", "05", "06", "07", "08", "09",
    "10", "11", "12", "15", "20", "25", "30", "35", "40", "45", "49",
    "66", "88",
)
CONTINUATION_INDICATOR = "-"
ENFORCE_AREA_B_STATEMENT_INDENT = True

# Generated DB2 block indentation. See open decision D-8.
ENFORCE_AREA_B_SQL_INDENT = False
AREA_B_SQL_MIN_INDENT = AREA_B_MIN_INDENT

SQL_BLOCK_START = "EXEC SQL"
SQL_BLOCK_END = "END-EXEC"
SQL_STATUS_BLOCK_START = "EVALUATE SQLCODE"
SQL_STATUS_BLOCK_END = "END-EVALUATE"

# NOTE: the converter holds an equivalent list in patterns/. Copied here
# on purpose. code_review must never import from the converter.
NON_PARAGRAPH_WORDS = frozenset({
    "ACCEPT", "ADD", "ALTER", "CALL", "CANCEL", "CLOSE", "COMMIT",
    "COMPUTE", "CONTINUE", "DELETE", "DISPLAY", "DIVIDE", "EJECT", "ELSE",
    "END-ADD", "END-CALL", "END-DELETE", "END-DIVIDE", "END-EVALUATE",
    "END-EXEC", "END-IF", "END-MULTIPLY", "END-PERFORM", "END-READ",
    "END-RETURN", "END-REWRITE", "END-SEARCH", "END-START", "END-STRING",
    "END-SUBTRACT", "END-UNSTRING", "END-WRITE", "EVALUATE", "EXEC",
    "EXIT", "FETCH", "GOBACK", "IF", "INITIALIZE", "INSPECT", "MOVE",
    "MULTIPLY", "NEXT", "OPEN", "PERFORM", "READ", "RETURN", "REWRITE",
    "ROLLBACK", "SEARCH", "SET", "SKIP1", "SKIP2", "SKIP3", "SORT",
    "SPACE", "SPACES", "START", "STOP", "STRING", "SUBTRACT", "UNSTRING",
    "WHEN", "WRITE",
})

# ---- CHK-07 sequence numbering continuity ----------------------------
LEFT_SEQUENCE_STEP = 10
RIGHT_SEQUENCE_STEP = 10000
ENFORCE_SEQUENCE_STEP = True
ALLOW_SEQUENCE_GAPS = False

# ---- CHK-08 DCLGEN include and copybook integrity --------------------
DCLGEN_GROUP_PREFIX = "DCL"
EXCLUDED_INCLUDE_NAMES = frozenset({"GEN", "SQLCA", "SQLERRWS", "SQLERROR"})
INCLUDE_STATEMENT_TEMPLATE = "EXEC SQL INCLUDE {name} END-EXEC."
FORBIDDEN_COPY_PREFIXES = ("IDMS",)
ENFORCE_INCLUDE_IN_WORKING_STORAGE = True

# COPY member validation. See open decision D-9.
ENFORCE_COPY_MEMBER_RESOLUTION = False
COPYBOOK_RECORD_LEVEL = "01"

# ---- Shared conversion markers ---------------------------------------
MISSING_MAPPING_MARKERS = (
    "CONVERSION SKIPPED",
    "MISSING SHEET MAPPING",
    "MISSING DCLGEN",
    "MISSING SELECT",
    "MISSING INSERT",
    "MISSING UPDATE",
    "MISSING DELETE",
    "MISSING MAPPING",
    "MISSING KEY COLUMN METADATA",
    "MISSING INSERT COLUMNS",
    "INCOMPLETE CONSERVATIVE UPDATE METADATA",
    "MANUAL REDESIGN",
)

SQL_LOCATION_MOVE_PREFIX = "MOVE '"
SQL_LOCATION_MOVE_SUFFIX = "TO SQL-LOCATION"
SQL_LOCATION_LOOKBACK = 6
ENFORCE_SQL_LOCATION_BEFORE_SQL = True

CONTINUE_STATEMENT = "CONTINUE"
NON_EXECUTABLE_SQL_VERBS = ("INCLUDE", "DECLARE", "WHENEVER", "BEGIN", "END")

# ---- Shared DB2 naming equivalences ----------------------------------
DB2_TABLE_SUFFIX_EQUIVALENTS = (
    ("_TB", "_TV"),
    ("_TV", "_TB"),
    ("TB", "TV"),
    ("TV", "TB"),
)
VARCHAR_SUBFIELD_SUFFIXES = ("-LEN", "-TEXT")

# ---- CHK-09 record retrieval conversion ------------------------------
RETRIEVAL_SQL_VERBS = ("SELECT", "OPEN", "FETCH", "CLOSE")
SELECT_REQUIRED_CLAUSES = ("FROM", "INTO", "WHERE")
ENFORCE_SELECT_WHERE = True

# ---- CHK-10 record modification conversion ---------------------------
WRITE_SQL_VERBS = ("INSERT", "UPDATE", "DELETE")
INSERT_REQUIRED_CLAUSES = ("INTO",)
UPDATE_REQUIRED_CLAUSES = ("SET", "WHERE")
DELETE_REQUIRED_CLAUSES = ("WHERE",)
UPDATE_QUERYNO = "442"
ENFORCE_QUERYNO = True

# ---- CHK-11 SQLCODE and COMMIT conversion ----------------------------
USE_EVALUATE_SQLCODE = True
SQLCODE_EVALUATE_START = "EVALUATE SQLCODE"
SQLCODE_EVALUATE_END = "END-EVALUATE"
SQLCODE_WHEN_OTHER = "WHEN OTHER"
SQLCODE_ZERO_BRANCHES = ("WHEN 0", "WHEN ZERO")
SQLCODE_NOT_FOUND_BRANCH = "WHEN 100"
END_OF_CURSOR_CONDITION = "SQLCODE = 100"
SQLCODE_LOOKAHEAD = 3

LEGACY_SQLCODE_FORMS = (
    "IF SQLCODE NOT = 0",
    "IF SQLCODE NOT= 0",
    "IF NOT SQLCODE = 0",
    "IF NOT SQLCODE = 100",
)

COMMIT_STATEMENT = "COMMIT"
IDMS_COMMIT_VERB = "FINISH"
EXECUTABLE_SQL_VERBS = (
    "SELECT", "INSERT", "UPDATE", "DELETE",
    "OPEN", "FETCH", "CLOSE", "COMMIT", "ROLLBACK",
)
SQLCODE_EXEMPT_VERBS = ("COMMIT", "ROLLBACK")

# A period inside an EVALUATE terminates the sentence and closes the
# scope, orphaning END-EVALUATE. Only the statement immediately before
# END-EVALUATE may carry one, and conventionally not even that.
ENFORCE_NO_PERIOD_IN_EVALUATE = True

# ---- CHK-12 cursor declaration standard ------------------------------
CURSOR_DECLARE_VERB = "DECLARE"
CURSOR_REQUIRED_CLAUSES = ("WITH HOLD", "FOR READ ONLY")
CURSOR_SELECT_CLAUSES = ("SELECT", "FROM")
CURSOR_SELECT_ALL = "SELECT *"
ENFORCE_CURSOR_WITH_HOLD = True
ENFORCE_CURSOR_FOR_READ_ONLY = True
ENFORCE_CURSOR_EXPLICIT_COLUMNS = True
CURSOR_DECLARATION_MARKER = "DB2 CURSOR DECLARATIONS"

# ---- CHK-13 cursor paragraph structure -------------------------------
CURSOR_OPERATIONS = ("OPEN", "FETCH", "CLOSE")
CURSOR_FETCH_OFFSET = 10
CURSOR_CLOSE_OFFSET = 20
CURSOR_OPEN_NUMBERS = (710, 810, 910)
ENFORCE_CURSOR_OPEN_NUMBERS = True
CURSOR_PARAGRAPH_MARKER = "DB2 GENERATED CURSOR OPEN FETCH CLOSE PARAGRAPHS"

# ---- CHK-14 end of cursor handling -----------------------------------
CURSOR_EOC_SUFFIX = "-EOC"
CURSOR_NOT_EOC_SUFFIX = "-NOT-EOC"
CURSOR_FLAGS_MARKER = "DB2 CURSOR END-OF-CURSOR FLAGS"
LEGACY_EOC_CONDITIONS = (
    "UNTIL SQLCODE = 100",
    "IF NOT SQLCODE = 100",
)
ENFORCE_EOC_FLAG_LOOP = True

# ---- CHK-15 nested cursor processing ---------------------------------
CHILD_CURSOR_MINIMUM_NUMBER = 800
CHILD_FETCH_EARLY_STOP_FIELD = "SW-STATUS-D"
# See open decision D-10.
ENFORCE_CHILD_FETCH_EARLY_STOP = False

# ---- CHK-16 conservative update column selection ---------------------
UPDATE_AUDIT_PREFIXES = (
    "TS_UPDATE", "ID_USERID", "NR_USERID", "ID_USER", "NR_USER",
)
INSERT_ONLY_AUDIT_PREFIXES = ("TS_CREATE",)
BROAD_UPDATE_RATIO = 0.8
ENFORCE_CONSERVATIVE_UPDATE = True

# ---- CHK-17 update WHERE key integrity -------------------------------
KEY_TEXT_MARKERS = ("PRIMARY", "KEY", "CALC")
IDENTITY_KEY_PREFIXES = ("NS_ID", "NR_ID", "ID_", "CO_ID", "NR_IS")
HOST_REFERENCE_MARKER = ":"
FORBIDDEN_WHERE_PREDICATES = ("1 = 1", "1=1")
ENFORCE_WHERE_HOST_VARIABLES = True
ENFORCE_WHERE_NO_FOREIGN_KEY = True

# ---- CHK-18 audit column and date handling ---------------------------
DATE_COLUMN_PREFIXES = ("DA_", "DT_")
DB2_DATE_SENTINEL = "00010101"
DATE_STAGING_FIELDS = ("DA-CCYYMMDD", "DA-CCYYMMDD-R", "DA-DD-MM-CCYY")
TIMESTAMP_SOURCE_FIELD = "TS-TIMESTAMP"
USER_SOURCE_FIELD = "CS-PROGRAM"
AUDIT_MOVE_LOOKBACK = 12
ENFORCE_AUDIT_MOVES_BEFORE_UPDATE = True
ENFORCE_DATE_STAGING = True

# ---- CHK-19 restart paragraph structure ------------------------------
RESTART_PARAGRAPHS = {
    "control": "700-RESTART-CONTROL",
    "restart_found": "710-JOB-IS-RESTART",
    "write_restart": "720-WRITE-RESTART-REC",
    "commit": "800-PROCESS-COMMIT",
    "abend": "810000-CALL-USERABEN",
}
RESTART_SQL_PARAGRAPH_PREFIX = "700-"
RESTART_SQL_OPERATIONS = ("SELECT", "UPDATE", "INSERT")
RESTART_ABEND_CALL = "CALL USERABEN"
RESTART_STATUS_COMPLETE = "1"
RESTART_STATUS_INCOMPLETE = "0"

# ---- CHK-20 restart SQL from DCLGEN metadata -------------------------
RESTART_TABLE_NAME_HINTS = ("RST", "RESTART")
# See open decision D-3.
ENFORCE_RESTART_QUERYNO = False
RESTART_SELECT_QUERYNO = "376"
RESTART_UPDATE_QUERYNO = "398"
RESTART_INSERT_QUERYNO = ""

# ---- CHK-21 unresolved restart metadata safe skip --------------------
RESTART_CONTROL_HINTS = (
    "RECAB", "RESTART", "RST", "CONTROL", "CTRL", "CHECKPOINT", "CHKPT",
)
RESTART_SKIP_MARKERS = (
    "MANUAL DB2 REDESIGN",
    "WAS NOT CONVERTED",
    "RESTART DCLGEN NOT RESOLVED",
    "RESTART FLOW NOT GENERATED",
    "MISSING SHEET MAPPING AND DCLGEN METADATA",
)

# ---- CHK-22 DB2 table and column naming authority --------------------
SQL_TABLE_KEYWORDS = ("FROM", "UPDATE", "INSERT INTO", "DELETE FROM")
ENFORCE_TABLE_AUTHORITY = True
ENFORCE_COLUMN_AUTHORITY = True

# ---- CHK-23 DCLGEN host variable name exactness ----------------------
HOST_QUALIFIER_KEYWORDS = ("OF", "IN")
ENFORCE_HOST_NAME_EXACTNESS = True

# ---- CHK-24 picture clause and length validation ---------------------
ENFORCE_PICTURE_LENGTH_MATCH = True
PICTURE_LENGTH_TOLERANCE = 0

# Sheet Mapping records STORED BYTES. A COBOL picture records POSITIONS.
# The two coincide only for character data: a DB2 DATE stores in 4 bytes
# but its host is PIC X(10), and a packed numeric stores in fewer bytes
# than it has digits. Comparing anything else produces noise.
COMPARABLE_LENGTH_TYPES = ("CHAR", "CHARACTER", "GRAPHIC")

# A VARCHAR host is a group with two 49-level children carrying the
# pictures. A group item has no PICTURE of its own, so its absence is
# correct COBOL rather than a defect.
VARCHAR_TYPES = (
    "VARCHAR", "VARGRAPHIC", "LONG VARCHAR", "LONG VARGRAPHIC",
    "CLOB", "DBCLOB", "BLOB",
)

# ---- CHK-25 copybook and record usage validation ---------------------
ENFORCE_NO_IDMS_QUALIFIER = True

# =====================================================================
# DECISIONS CLOSED BY THE MANUAL REFERENCE PROGRAM (VMDZ4420)
#
# Appended deliberately: these assignments override any earlier value in
# this file. Fold them into their CHK- sections when convenient.
# =====================================================================

# ---- CHK-04 compiler option and PROGRAM-ID
#
# The manual reference declares CS-PROGRAM as a subordinate 10-level inside
# 01 WS-TE-WORK, not as 01 or 77. Decision D-2 closed by evidence.
CS_PROGRAM_FIELD = "CS-PROGRAM"
CS_PROGRAM_PICTURE = "PIC X(8)"
CS_PROGRAM_LEVELS = (
    "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "77",
)

# The manual reference emits no END PROGRAM statement.
ENFORCE_END_PROGRAM = False

# ---- CHK-05 SQL error paragraph and routing
#
# Manual reference body:
#     EXEC SQL
#          INCLUDE SQLERROR
#     END-EXEC.
# It declares no SQLERROR paragraph of its own; the copybook supplies the
# routine. Decision D-1 closed by evidence. Set to () to skip criterion 08.
SQL_ERROR_BODY = ("EXEC SQL", "INCLUDE SQLERROR", "END-EXEC")
SQL_ERROR_INCLUDE = "INCLUDE SQLERROR"

# ---- CHK-06 Area A and Area B alignment
#
# Manual reference places EXEC SQL, EVALUATE SQLCODE and END-EVALUATE at
# column 12. Decision D-8 closed by evidence.
ENFORCE_AREA_B_SQL_INDENT = True

# ---- CHK-15 nested cursor processing
#
# Manual reference:
#     PERFORM 820-FETCH-DZEVEFC1 UNTIL DZEVEFC1-EOC OR
#                                      SW-STATUS-D = 'Y'
# Decision D-10 closed by evidence.
ENFORCE_CHILD_FETCH_EARLY_STOP = True

# ---- CHK-20 restart SQL from DCLGEN metadata
#
# rules/update_restart_rules.py and this file agree: 376 / 398 / 413.
# The recorded conflict was a blank INSERT value here, not a disagreement
# between modules. Decision D-3 closed.
ENFORCE_RESTART_QUERYNO = True
RESTART_SELECT_QUERYNO = "376"
RESTART_UPDATE_QUERYNO = "398"
RESTART_INSERT_QUERYNO = "413"
# ---- CHK-02 SQL-LOCATION ownership
#
# SQLERRWS supplies SQL-LOCATION. A local declaration is a duplicate
# data-name. Decision closed by the manual reference program.
ENFORCE_SQL_LOCATION_DECLARATION = False