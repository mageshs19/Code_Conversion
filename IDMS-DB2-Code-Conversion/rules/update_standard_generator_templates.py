from __future__ import annotations

# Update standard generator COBOL templates and literals.
#
# This module owns ALL generated COBOL layout text so the generator holds
# no COBOL literals. Only dynamic values (record, field, table, host names)
# are substituted at fill time. No program/record/table names are hardcoded;
# those arrive as .format() kwargs from resolved metadata.

# --- Numeric / literal constants used in generated COBOL ---
RESTART_LENGTH_BASE = 15            # added to record length for WS-RESTART-LEN
EOF_NOT_SET_VALUE = "N"
EOF_SET_VALUE = "Y"
COMMIT_COUNTER_RESET_VALUE = "0"

# --- Shared generated symbol names (not program-specific) ---
CS_PROGRAM_FIELD = "CS-PROGRAM"
DA_DD_MM_CCYY_FIELD = "DA-DD-MM-CCYY"
COMMIT_COUNTER_LEGACY = "WS-TELLER"
SQL_ERROR_PARAGRAPH = "SQLERROR"
ABEND_CALL_STATEMENT = "CALL USERABEN"

# --- Display strings ---
DISPLAY_PREVIOUS_RUN_COMPLETE = "DISPLAY ' PREVIOUS RUN COMPLETE '"
DISPLAY_ERROR_REC_TEMPLATE = "DISPLAY 'ERROR REC NUMBER : ' {counter}"

# --- Include templates ---
COPYBOOK_INCLUDE_TEMPLATE = "COPY {include}."
DCLGEN_INCLUDE_TEMPLATE = "EXEC SQL INCLUDE {include} END-EXEC."

# --- Working-storage template ---
WORKING_STORAGE_TEMPLATE = """01 {switch_group}.
   02 SW-{record} PIC X VALUE '{eof_not}'.
      88 {record}-NOT-EOF VALUE '{eof_not}'.
      88 {record}-EOF     VALUE '{eof_set}'.

01 {help_group}.
   02 {restart_record}.
      03 {read_count}     PIC 9(15).
      03 {restart_key}  PIC X({length}).

   02 {input_save_area} PIC X({length}).

   02 {commit_counter}         PIC 9(9) COMP-3 VALUE ZERO.
   02 {input_counter} PIC 9(7) COMP-3 VALUE ZERO.
   02 {update_counter}  PIC S9(11) COMP-3 VALUE +0.
   02 {restart_len}    PIC 9(5) VALUE {restart_length}."""

# --- READ flat file template ---
READ_FLAT_FILE_TEMPLATE = """READ-FLAT-FILE.

    INITIALIZE {record}.

    READ {file_name} INTO {record}
        AT END
            SET {record}-EOF TO TRUE
    END-READ.

    IF {record}-NOT-EOF
        ADD +1 TO {commit_counter}
        ADD +1 TO {input_counter}
        MOVE {record} TO {input_save_area}
    END-IF."""

# --- Restart control template ---
RESTART_CONTROL_TEMPLATE = """{control}.

    MOVE {cs_program}
      TO {program_field} OF {host_record}.

    MOVE {da_field}
      TO {date_field} OF {host_record}.

    MOVE {default_phase}
      TO {phase_field} OF {host_record}.

    PERFORM {select}.

    EVALUATE SQLCODE
        WHEN 0
            PERFORM {restart_found}
        WHEN 100
            PERFORM {write_restart}
        WHEN OTHER
            PERFORM {sql_error}
    END-EVALUATE.

    MOVE {commit_reset} TO {commit_counter_legacy}."""

# --- Restart found template ---
RESTART_FOUND_TEMPLATE = """{restart_found}.

    MOVE {payload_text_field} OF {host_record}
      TO {restart_record}.

    IF {status_field} OF {host_record} = '{status_complete}'
        {display_complete}
        PERFORM {abend}
    ELSE
        PERFORM {read_count} OF {restart_record} TIMES
            PERFORM READ-FLAT-FILE
            MOVE {read_count} OF {restart_record}
              TO {input_counter}
        END-PERFORM
    END-IF."""

# --- Write restart template ---
WRITE_RESTART_TEMPLATE = """{write_restart}.

    MOVE '{status_incomplete}'
      TO {status_field} OF {host_record}.

    MOVE {retention_days}
      TO {retention_field} OF {host_record}.

    MOVE {restart_len}
      TO {payload_len_field} OF {host_record}.

    MOVE 0
      TO {input_counter}.

    MOVE {input_counter}
      TO {read_count} OF {restart_record}.

    INITIALIZE {restart_key} OF {restart_record}.

    MOVE {restart_record}
      TO {payload_text_field} OF {host_record}.

    PERFORM {insert}."""

# --- Process commit template ---
PROCESS_COMMIT_TEMPLATE = """{commit}.

    MOVE 0 TO {commit_counter}.

    MOVE {input_counter}
      TO {read_count} OF {restart_record}.

    MOVE {input_save_area}
      TO {restart_key} OF {restart_record}.

    IF {record}-EOF
        MOVE '{status_complete}'
          TO {status_field} OF {host_record}
    ELSE
        MOVE '{status_incomplete}'
          TO {status_field} OF {host_record}
    END-IF.

    MOVE {restart_len}
      TO {payload_len_field} OF {host_record}.

    MOVE {restart_record}
      TO {payload_text_field} OF {host_record}.

    PERFORM {update}.

    EXEC SQL
        COMMIT
    END-EXEC.

    EVALUATE SQLCODE
        WHEN 0
            CONTINUE
        WHEN OTHER
            {display_error}
            PERFORM {sql_error}
    END-EVALUATE."""

# --- Restart SQL template (SELECT / UPDATE / INSERT / ABEND) ---
RESTART_SQL_TEMPLATE = """{select}.

    EXEC SQL
        SELECT {program_column}
             , {phase_column}
             , {date_column}
             , {status_column}
             , {retention_column}
             , {payload_column}
          INTO :{host_record}.{program_field}
             , :{host_record}.{phase_field}
             , :{host_record}.{date_field}
             , :{host_record}.{status_field}
             , :{host_record}.{retention_field}
             , :{host_record}.{payload_group}
          FROM {table_name}
         WHERE {program_column} = :{host_record}.{program_field}
           AND {phase_column} = :{host_record}.{phase_field}
           AND {date_column} = :{host_record}.{date_field}
        QUERYNO {select_queryno}
    END-EXEC.

    EVALUATE SQLCODE
        WHEN 0
            CONTINUE
        WHEN 100
            CONTINUE
        WHEN OTHER
            {display_error}
            PERFORM {sql_error}
    END-EVALUATE.

{update}.

    EXEC SQL
        UPDATE {table_name}
           SET {payload_column} = :{host_record}.{payload_group}
             , {status_column}  = :{host_record}.{status_field}
         WHERE {program_column} = :{host_record}.{program_field}
           AND {phase_column} = :{host_record}.{phase_field}
           AND {date_column} = :{host_record}.{date_field}
        QUERYNO {update_queryno}
    END-EXEC.

    EVALUATE SQLCODE
        WHEN 0
            CONTINUE
        WHEN OTHER
            {display_error}
            PERFORM {sql_error}
    END-EVALUATE.

{insert}.

    EXEC SQL
        INSERT INTO {table_name}
        VALUES (:{host_record})
        QUERYNO {insert_queryno}
    END-EXEC.

    EVALUATE SQLCODE
        WHEN 0
            CONTINUE
        WHEN OTHER
            {display_error}
            PERFORM {sql_error}
    END-EVALUATE.

{abend}.

    {abend_call}."""

# LOCATION: rules/update_standard_generator_templates.py
# ACTION: APPEND

# Standard SQLERROR paragraph. Every generated "WHEN OTHER" branch does
# "PERFORM SQLERROR", so this target paragraph must be declared once at the
# end of PROCEDURE DIVISION. Minimal manual-standard body: report location +
# SQLCODE, then abend via USERABEN.
SQLERROR_PARAGRAPH_TEMPLATE = [
    "SQLERROR.",
    "     DISPLAY 'SQL ERROR AT : ' SQL-LOCATION.",
    "     DISPLAY 'SQLCODE      : ' SQLCODE.",
    "     CALL USERABEN.",
]