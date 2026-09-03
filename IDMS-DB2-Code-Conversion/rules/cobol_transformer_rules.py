from __future__ import annotations

"""
Rules/constants for COBOL source transformation.

No regex patterns or transformer logic belong here.
"""


COBOL_TRANSFORMER_RULES = [
    "Preserve original COBOL business flow.",
    "Convert CBL compiler option line to DB2-compatible option.",
    "Replace target PROGRAM-ID only when requested.",
    "Remove residual IDMS declarative/control lines.",
    "Remove or convert residual IDMS executable lines.",
    "Preserve sequence/spacing for one-line DB condition replacements.",
    "Remove orphan IDMS-ABORT paragraph after PERFORM IDMS-ABORT is removed.",
]


DB2_COMPILER_OPTION_LINE = "CBL ARITH(EXTEND)"


DEFAULT_SQL_ERROR_PARAGRAPH = "SQL-ERROR"


GENERATED_LINE_PREFIXES = (
    "* DB2:",
    "EXEC SQL",
    "END-EXEC",
    "MOVE '",
    "PERFORM ",
    "END-IF",
    "CONTINUE",
    "SELECT",
    "INSERT",
    "UPDATE",
    "DELETE",
    "COMMIT",
    "ROLLBACK",
)