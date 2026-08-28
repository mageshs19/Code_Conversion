# LOCATION: src/idms_db2_phase2/composers/update_sql_cleanup/sqlerror_normalizer.py
# ACTION: CREATE NEW FILE

"""Normalizes malformed 'PERFORM SQLERROR.END-IF.' lines."""

from __future__ import annotations


class SqlerrorNormalizer:
    def __init__(self, owner) -> None:
        self.owner = owner

    def normalize(self, text: str) -> str:
        output: list[str] = []
        changed = False

        for line in text.splitlines():
            logical = self.owner._logical(line)
            match = self.owner.MALFORMED_SQLERROR_ENDIF_PATTERN.match(logical)

            if not match:
                output.append(line)
                continue

            leading = self.owner._leading_spaces(line)
            output.append(f"{leading}PERFORM SQLERROR.")
            output.append(f"{leading}END-IF.")
            changed = True

        if changed:
            self.owner.messages.append(
                "Update SQL cleanup: normalized malformed "
                "PERFORM SQLERROR.END-IF."
            )

        return "\n".join(output).rstrip() + "\n"