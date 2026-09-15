"""Read-only fixed-format COBOL inspection.

Layout: cols 1-6 left sequence, col 7 indicator,
        cols 8-72 body, cols 73-80 right sequence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

WIDTH = 80
IND = 6
BODY_A, BODY_B = 7, 72
RSEQ_A, RSEQ_B = 72, 80
COMMENTS = ("*", "/")
VALID_INDICATORS = (" ", "*", "/", "D", "-")
AREA_B_MIN = 4

_SEQ_IN_BODY = re.compile(r"^\s*\d{6}\s")


@dataclass(frozen=True)
class Line:
    number: int
    raw: str

    @property
    def is_fixed(self) -> bool:
        return (
            len(self.raw) >= WIDTH
            and self.raw[0:6].isdigit()
            and self.raw[RSEQ_A:RSEQ_B].isdigit()
        )

    @property
    def left_sequence(self) -> str:
        return self.raw[0:6] if self.is_fixed else ""

    @property
    def right_sequence(self) -> str:
        return self.raw[RSEQ_A:RSEQ_B] if self.is_fixed else ""

    @property
    def indicator(self) -> str:
        return self.raw[IND] if len(self.raw) > IND else " "

    @property
    def body(self) -> str:
        return self.raw[BODY_A:BODY_B] if self.is_fixed else self.raw

    @property
    def logical(self) -> str:
        return self.body.strip().upper()

    @property
    def indent(self) -> int:
        b = self.body
        return len(b) - len(b.lstrip())

    @property
    def is_blank(self) -> bool:
        return not self.body.strip()

    @property
    def is_comment(self) -> bool:
        return self.indicator in COMMENTS or self.body.lstrip().startswith(COMMENTS)

    @property
    def is_code(self) -> bool:
        return not self.is_blank and not self.is_comment

    @property
    def has_sequence_in_body(self) -> bool:
        return bool(_SEQ_IN_BODY.match(self.body))

    @property
    def overflow(self) -> str:
        return self.raw[BODY_B:RSEQ_A]


class CobolView:
    def __init__(self, text: str) -> None:
        clean = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
        self.lines = [Line(i, v) for i, v in enumerate(clean.split("\n"), start=1)]

    @property
    def populated(self) -> list[Line]:
        return [l for l in self.lines if l.raw.strip()]

    @property
    def code(self) -> list[Line]:
        return [l for l in self.lines if l.is_code]

    @property
    def comments(self) -> list[Line]:
        return [l for l in self.lines if l.is_comment]

    @property
    def code_text(self) -> str:
        return "\n".join(l.logical for l in self.code)

    @property
    def all_text(self) -> str:
        return "\n".join(l.logical for l in self.lines)

    @property
    def is_empty(self) -> bool:
        return not any(l.raw.strip() for l in self.lines)

    # ---- queries ----------------------------------------------------------
    def has_code_token(self, token: str) -> bool:
        return str(token).upper() in self.code_text

    def has_token(self, token: str) -> bool:
        return str(token).upper() in self.all_text

    def code_with(self, token: str) -> list[Line]:
        t = str(token).upper()
        return [l for l in self.code if t in l.logical]

    def starting_with(self, prefix: str) -> list[Line]:
        p = str(prefix).upper()
        return [l for l in self.code if l.logical.startswith(p)]

    def matching(self, pattern: re.Pattern) -> list[Line]:
        return [l for l in self.code if pattern.match(l.logical)]

    def searching(self, pattern: re.Pattern) -> list[Line]:
        return [l for l in self.code if pattern.search(l.logical)]

    def exact(self, text: str) -> list[Line]:
        t = str(text).strip().upper()
        return [l for l in self.code if l.logical == t]

    def count_of(self, text: str) -> int:
        return self.all_text.count(str(text).upper())

    def first_group(self, pattern: re.Pattern, group: str) -> str:
        for l in self.code:
            m = pattern.match(l.logical)
            if m:
                return m.group(group)
        return ""

    def paragraph_exists(self, name: str) -> bool:
        return bool(self.exact(f"{str(name).upper()}."))

    # ---- sequence ---------------------------------------------------------
    def sequence(self, right: bool = False) -> list[int]:
        out = []
        for l in self.lines:
            if not l.is_fixed:
                continue
            v = l.right_sequence if right else l.left_sequence
            if v.isdigit():
                out.append(int(v))
        return out

    @staticmethod
    def constant_step(values: list[int]) -> int | None:
        if len(values) < 2:
            return None
        step = values[1] - values[0]
        if step <= 0:
            return None
        return step if all(b - a == step for a, b in zip(values, values[1:])) else None