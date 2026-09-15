# LOCATION: rules/sequence_artifact_rules.py
# ACTION: CREATE NEW FILE

"""Sequence artifact cleanup rules.

Constants only. No regex, no runtime logic, no program / record / table /
cursor / paragraph / host variable names.
"""

from __future__ import annotations

# =====================================================================
# Master switch
# =====================================================================
ENFORCE_SEQUENCE_ARTIFACT_CLEANUP = True

# =====================================================================
# Sentence repair
# =====================================================================
# Removing an artifact can strip the period that closed the preceding
# sentence. Without repair the sentence runs into the next paragraph
# header and the compiler rejects the program.
REPAIR_EXPOSED_SENTENCE = True
PARAGRAPH_TERMINATOR = "."

# A period is added only after a statement that can legitimately end a
# COBOL sentence. Adding one after, say, a WHEN branch would close an
# EVALUATE scope early and orphan END-EVALUATE.
SENTENCE_CARRIERS = frozenset(
    {
        "END-IF",
        "END-EVALUATE",
        "END-PERFORM",
        "END-READ",
        "END-SEARCH",
        "END-STRING",
        "END-WRITE",
        "CONTINUE",
        "WRITE",
        "MOVE",
        "ADD",
        "SUBTRACT",
        "COMPUTE",
        "PERFORM",
        "DISPLAY",
        "CALL",
        "INITIALIZE",
        "SET",
        "OPEN",
        "CLOSE",
        "READ",
        "REWRITE",
        "GOBACK",
        "STOP",
    }
)

# =====================================================================
# Diagnostics
# =====================================================================
SEQUENCE_ARTIFACT_MESSAGES = {
    "removed": (
        "Sequence artifact: removed stale source sequence line '{body}'."
    ),
    "terminated": (
        "Sequence artifact: restored sentence terminator after "
        "'{statement}'."
    ),
    "summary": (
        "Sequence artifact: removed {removed} artifact line(s), "
        "repaired {repaired} sentence(s)."
    ),
}