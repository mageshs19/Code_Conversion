# LOCATION: src/idms_db2_phase2/composers/record_materialisation/record_picture_sizer.py
# ACTION: REPLACE ENTIRE FILE

"""Sizes a COBOL PICTURE clause in stored bytes.

Pure measurement. Given a data description line it answers one question:
how many bytes does this entry occupy? Getting that wrong silently
shifts every field of a fixed-length record.

WHY THIS MODULE OWNS NO REGEX
------------------------------
The project rule puts regex in patterns/. This module is the documented
exception, and the exception is earned:

    PIC 9999    -> 4      correct
    PIC 9(7)    -> 1      wrong
    PIC X(478)  -> 1      wrong

PICTURE_SYMBOL_PATTERN captures the symbol and exposes no repeat group,
so every clause written with (n) collapsed to the count of literal
symbols. F-FORM measured 1 byte, the length guard refused a 432-byte
VMBFAS layout as "longer than the 1 byte F-FORM declares", and roughly
400 lines of generated output were discarded on every run.

Three separate attempts to fix that through the shared pattern module
produced identical wrong answers, because a pattern this module cannot
see is a dependency this module cannot verify. Counting repeat groups is
character arithmetic, not pattern matching, so it is done here, in full
view, where a unit test pins every branch.

No regex. No imports. No hidden behaviour.
"""

from __future__ import annotations

# Picture symbols that occupy a stored character position.
# S and V are sign and implied decimal point: neither is stored.
COUNTED_SYMBOLS = frozenset("X9AZ")

# Packed decimal halves the stored length.
COMP_3_SYMBOLS = ("COMPUTATIONAL-3", "COMP-3", "PACKED-DECIMAL")
COMP_3_SYMBOL = "COMP-3"

# The PICTURE keyword, longest form first.
PIC_KEYWORDS = ("PICTURE", "PIC")

# Clauses that may follow a PICTURE on the same entry. Reading past one
# of these counts the A of VALUE and the A of USERABEN in
#
#     77  USERABEN  PIC X(8)  VALUE 'USERABEN'.
#
# and reports 10 bytes instead of 8.
STOP_WORDS = frozenset({
    "BLANK",
    "BINARY",
    "COMP",
    "COMP-1",
    "COMP-2",
    "COMP-3",
    "COMP-4",
    "COMPUTATIONAL",
    "COMPUTATIONAL-1",
    "COMPUTATIONAL-2",
    "COMPUTATIONAL-3",
    "COMPUTATIONAL-4",
    "DISPLAY",
    "INDEXED",
    "JUST",
    "JUSTIFIED",
    "OCCURS",
    "PACKED-DECIMAL",
    "REDEFINES",
    "SIGN",
    "SYNC",
    "SYNCHRONIZED",
    "USAGE",
    "VALUE",
    "VALUES",
})

# Characters that may appear inside a COBOL data name. A keyword is only
# a keyword when it is not part of a longer name, so WS-PIC-CODE never
# looks like a PICTURE clause.
NAME_CHARACTERS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
)

PICTURE_GROUP = "picture"
OPEN_PAREN = "("
CLOSE_PAREN = ")"
PERIOD = "."


class RecordPictureSizer:
    """Measures a PICTURE clause, never under-reporting."""

    #
    # Public entry points
    #
    @classmethod
    def declared_bytes(cls, body: str, match=None) -> int:
        """Stored byte count of one data description entry.

        `body`  the full logical line, e.g. "05  F-FORM  PIC X(478)."
        `match` the caller's regex match. Its 'picture' group is ONE
                candidate, never the answer: it has been observed to
                capture 'X' where the line says 'X(478)'.

        Every candidate is measured and the LARGEST wins. A PICTURE can
        never declare fewer positions than its most complete reading, so
        the maximum can only correct a truncated read.
        """
        text = str(body or "")
        packed = cls.is_comp_3(text)

        sizes = [
            cls.size_of(candidate, COMP_3_SYMBOL if packed else "")
            for candidate in cls.candidates(text, match)
        ]

        return max(sizes) if sizes else 0

    @classmethod
    def size_of(cls, picture: str, usage: str = "") -> int:
        """Character positions of a PICTURE, honouring repeat counts.

            X(10)         -> 10
            XXX           ->  3
            9(7)          ->  7
            9999          ->  4
            X(4 )         ->  4    whitespace inside the parentheses
            S9(13)V99     -> 15    S and V are not stored
            S9(11) COMP-3 ->  6    (11 // 2) + 1
        """
        text = str(picture or "").upper()

        if not text:
            return 0

        digits = 0
        index = 0
        length = len(text)

        while index < length:
            if text[index] not in COUNTED_SYMBOLS:
                index += 1
                continue

            index += 1
            repeat, index = cls._repeat_at(text, index)
            digits += repeat if repeat else 1

        if not digits:
            return 0

        if cls.is_comp_3(usage) or cls.is_comp_3(text):
            return (digits // 2) + 1

        return digits

    @classmethod
    def picture_bytes(cls, picture: str) -> int:
        """Back-compatible entry point for callers that pass a clause."""
        return cls.size_of(picture, picture)

    #
    # Candidates
    #
    @classmethod
    def candidates(cls, body: str, match=None) -> list[str]:
        """Every readable form of this entry's PICTURE, unordered."""
        out: list[str] = []

        captured = cls._group(match, PICTURE_GROUP)
        if captured:
            out.append(captured)

        clause = cls.clause_of(body)
        if clause:
            out.append(clause)

        # A caller may hand over a bare clause with no PIC keyword.
        if not clause and body and not cls._has_pic_keyword(str(body)):
            out.append(str(body))

        return out

    @classmethod
    def clause_of(cls, body: str) -> str:
        """The PICTURE clause of a data description line, bounded.

        Returns '' when the line carries no PICTURE.
        """
        text = str(body or "")
        upper = text.upper()

        start = -1
        keyword_length = 0

        for keyword in PIC_KEYWORDS:
            position = cls._find_word(upper, keyword)

            if position >= 0:
                start = position
                keyword_length = len(keyword)
                break

        if start < 0:
            return ""

        tokens = text[start + keyword_length :].split()

        if tokens and tokens[0].upper() == "IS":
            tokens = tokens[1:]

        kept: list[str] = []

        for token in tokens:
            if token.upper().strip(PERIOD) in STOP_WORDS:
                break
            kept.append(token)

        return " ".join(kept).strip().rstrip(PERIOD)

    @staticmethod
    def is_comp_3(text: str) -> bool:
        upper = str(text or "").upper()
        return any(symbol in upper for symbol in COMP_3_SYMBOLS)

    #
    # Character arithmetic
    #
    @staticmethod
    def _repeat_at(text: str, index: int) -> tuple[int, int]:
        """Read an optional '( n )' starting at `index`.

        Returns (repeat, next_index). repeat is 0 when the symbol
        carries no parenthesised count, and `next_index` is then
        unchanged, so the caller charges one position for the symbol.
        """
        length = len(text)
        cursor = index

        while cursor < length and text[cursor].isspace():
            cursor += 1

        if cursor >= length or text[cursor] != OPEN_PAREN:
            return 0, index

        cursor += 1

        while cursor < length and text[cursor].isspace():
            cursor += 1

        digits = ""

        while cursor < length and text[cursor].isdigit():
            digits += text[cursor]
            cursor += 1

        while cursor < length and text[cursor].isspace():
            cursor += 1

        if cursor >= length or text[cursor] != CLOSE_PAREN or not digits:
            return 0, index

        return int(digits), cursor + 1

    @staticmethod
    def _find_word(upper: str, word: str) -> int:
        """Index of `word` in `upper` when it stands as a whole token."""
        start = 0

        while True:
            position = upper.find(word, start)

            if position < 0:
                return -1

            before_ok = (
                position == 0
                or upper[position - 1] not in NAME_CHARACTERS
            )
            after = position + len(word)
            after_ok = (
                after >= len(upper)
                or upper[after] not in NAME_CHARACTERS
            )

            if before_ok and after_ok:
                return position

            start = position + 1

    @classmethod
    def _has_pic_keyword(cls, body: str) -> bool:
        upper = str(body or "").upper()
        return any(
            cls._find_word(upper, keyword) >= 0 for keyword in PIC_KEYWORDS
        )

    @staticmethod
    def _group(match, name: str) -> str:
        if match is None:
            return ""

        try:
            return str(match.group(name) or "").strip()
        except (IndexError, KeyError, AttributeError, TypeError):
            return ""


__all__ = ["COMP_3_SYMBOL", "COUNTED_SYMBOLS", "RecordPictureSizer"]